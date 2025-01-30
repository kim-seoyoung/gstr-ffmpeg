import socket
import struct
import ffmpeg
import cv2
import numpy as np

class RTPStreamDecoder:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.current_frame = b''
        self.packet_buffer = []
        self.sps_pps = []
        self.ts = -1
        self.seq = -1

        self.start_ffmpeg()

    def start_ffmpeg(self):
        """
        FFmpeg 파이프라인 생성
        """
        self.ffmpeg_process = (
            ffmpeg
            .input('pipe:0', format='h264')  # H.264 데이터를 파이프로 입력
            .output('pipe:', format='rawvideo', pix_fmt='bgr24')  # 디코딩된 프레임 출력
            .run_async(pipe_stdout=True, pipe_stdin=True, pipe_stderr=True)
        )

    def start(self):
        # UDP 소켓 생성 및 바인딩
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print(f"Listening for RTP packets on {self.host}:{self.port}")

        while True:
            # UDP 패킷 수신
            data, addr = sock.recvfrom(2048)

            # RTP 헤더와 페이로드 분리
            if len(data) >= 12:
                rtp_header, payload = self.parse_rtp_packet(data)
                if rtp_header:
                    self.handle_payload(rtp_header, payload)

    def parse_rtp_packet(self, data):
        """
        RTP 헤더를 파싱하고 페이로드를 반환
        """
        header = struct.unpack('!BBHII', data[:12])  # RTP 헤더 파싱
        version = (header[0] >> 6) & 0x03           # 버전
        if version != 2:  # RTP 버전 확인 (2가 아니면 무시)
            print('??')
            return None, None

        payload_type = header[1] & 0x7F             # 페이로드 타입
        sequence_number = header[2]                 # 시퀀스 번호
        timestamp = header[3]                       # 타임스탬프
        ssrc = header[4]                            # SSRC 식별자
        payload = data[12:]                         # RTP 페이로드

        print(f"RTP Packet - Payload Type: {payload_type}, Sequence: {sequence_number}, "
              f"Timestamp: {timestamp}, SSRC: {ssrc}")

        return {'sequence_number': sequence_number, 'timestamp': timestamp}, payload

    def handle_payload(self, rtp_header, payload):
        """
        RTP 페이로드 처리 및 NAL 조립
        """

        nal_type = payload[0] & 0x1F  # NAL 유형 추출
        print(f'nal type: {nal_type}')

        if nal_type == 9:  # AUD (무시)
            return

        if nal_type == 28:  # FU-A (Fragmented Unit)
            start_bit = (payload[1] & 0x80) >> 7
            end_bit = (payload[1] & 0x40) >> 6

            if start_bit == 1:
                nal_header = (payload[0] & 0xE0) | (payload[1] & 0x1F)
                self.current_frame = b'\x00\x00\x00\x01' + bytes([nal_header]) + payload[2:]
            else:
                self.current_frame += payload[2:]

            if end_bit == 1:
                self.packet_buffer.append(self.current_frame)
                self.current_frame = b''

        elif nal_type in [7, 8]:  # SPS, PPS
            self.packet_buffer.append(b'\x00\x00\x00\x01' + payload)
            self.sps_pps.append(payload)

        elif nal_type == 1:  # Non-IDR Frame
            if not self.has_sps_pps():
                print("Skipping P-Frame: SPS/PPS missing!")
                return
            self.packet_buffer.append(b'\x00\x00\x00\x01' + payload)

        if self.ts != rtp_header['timestamp']:
            if self.packet_buffer:
                nal_data = b''.join(self.packet_buffer)
                # self.decode_h264(nal_data)
            self.packet_buffer = []
            self.ts = rtp_header['timestamp']

    def has_sps_pps(self):
        """
        SPS & PPS가 수신되었는지 확인
        """
        return len(self.sps_pps) > 0
    
    def decode_h264(self, h264_data):
        # FFmpeg로 데이터 전달
        self.ffmpeg_process.stdin.write(h264_data)
        self.ffmpeg_process.stdin.flush()  # 버퍼 강제 비우기
        print('done?')

        # FFmpeg로부터 디코딩된 프레임 읽기
        width, height = 320, 240
        frame_size = width * height * 3
        raw_frame = self.ffmpeg_process.stdout.read(frame_size)
        print('done2?')
        if len(raw_frame) == frame_size:
            # 프레임 디스플레이
            self.display_frame(raw_frame, width, height)

    def display_frame(self, raw_frame, width, height):
        """
        디코딩된 프레임을 OpenCV로 디스플레이
        """
        

        frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))
        cv2.imshow('RTP Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.cleanup()

    def cleanup(self):
        """
        리소스 정리 및 종료
        """
        print("Cleaning up...")
        self.ffmpeg_process.stdin.close()
        self.ffmpeg_process.stdout.close()
        self.ffmpeg_process.wait()
        cv2.destroyAllWindows()
        exit()

# 실행
if __name__ == "__main__":
    rtp_decoder = RTPStreamDecoder(host="127.0.0.1", port=5000)
    rtp_decoder.start()
