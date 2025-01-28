import socket
import struct
import cv2
import numpy as np

class RTPStreamDecoder:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.packet_buffer = {}

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
                    self.process_payload(rtp_header, payload)

    def parse_rtp_packet(self, data):
        """
        RTP 헤더를 파싱하고 페이로드를 반환
        """
        header = struct.unpack('!BBHII', data[:12])  # RTP 헤더 파싱
        version = (header[0] >> 6) & 0x03           # 버전
        if version != 2:  # RTP 버전 확인 (2가 아니면 무시)
            return None, None

        payload_type = header[1] & 0x7F             # 페이로드 타입
        sequence_number = header[2]                 # 시퀀스 번호
        timestamp = header[3]                       # 타임스탬프
        ssrc = header[4]                            # SSRC 식별자
        payload = data[12:]                         # RTP 페이로드

        print(f"RTP Packet - Payload Type: {payload_type}, Sequence: {sequence_number}, "
              f"Timestamp: {timestamp}, SSRC: {ssrc}")

        return {'sequence_number': sequence_number, 'timestamp': timestamp}, payload

    def process_payload(self, rtp_header, payload):
        """
        RTP 페이로드 처리 (재조립 및 디코딩)
        """
        sequence_number = rtp_header['sequence_number']
        self.packet_buffer[sequence_number] = payload

        # 패킷 버퍼를 정렬하여 H.264 스트림 생성
        sorted_sequence_numbers = sorted(self.packet_buffer.keys())
        h264_data = b''.join(self.packet_buffer[seq] for seq in sorted_sequence_numbers)
        print('***', len(h264_data))
        # 디코딩 가능한 경우 처리
        frame = self.decode_h264(h264_data)
        print(frame)
        if frame is not None:
            self.display_frame(frame)

    def decode_h264(self, h264_data):
        """
        H.264 데이터를 디코딩하여 OpenCV 프레임 생성
        """
        # H.264 데이터 -> NumPy 배열
        np_array = np.frombuffer(h264_data, np.uint8)
        # OpenCV에서 디코딩
        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        return frame

    def display_frame(self, frame):
        """
        OpenCV로 프레임 디스플레이
        """
        cv2.imshow('RTP Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            exit()

# 실행
if __name__ == "__main__":
    rtp_decoder = RTPStreamDecoder(host="0.0.0.0", port=5000)
    rtp_decoder.start()
