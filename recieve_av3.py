import socket
import struct
import av.stream
import cv2
import numpy as np
import av

class RTPStreamDecoder:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.packet_buffer = []
        self.fu_buffer = []
        self.sps = None
        self.pps = None 

        self.codec = av.CodecContext.create('h264', 'r')

        self.nal_buffer = ''

    def start(self):
        # UDP 소켓 생성 및 바인딩
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print(f"Listening for RTP packets on {self.host}:{self.port}")

        frm_cnt = 0
        while True:
            # UDP 패킷 수신
            data, addr = sock.recvfrom(4096)

            # RTP 헤더와 페이로드 분리
            if len(data) >= 12:
                rtp_header, payload = self.parse_rtp_packet(data)
                if rtp_header:
                    frm = self.process_payload(rtp_header, payload)
                    if frm is not None and len(frm) > 0 and self.sps and self.pps:
                        # with open(f'./data/frm_{frm_cnt}_r.txt', 'wb') as f:
                        #     f.write(frm)
                        # frm_cnt += 1
                        self.decode_h264(frm)

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

        # print(f"RTP Packet - Payload Type: {payload_type}, Sequence: {sequence_number}, "
        #       f"Timestamp: {timestamp}, SSRC: {ssrc}")

        return {'sequence_number': sequence_number, 'timestamp': timestamp}, payload

    def process_payload(self, rtp_header, payload):
        nal_header = struct.unpack('!B', payload[0:1])[0]

        f = nal_header >> 7
        nri = (nal_header & 0x60) >> 5
        pl_type = nal_header & 0x1F
        print(f'f: {f}, nri: {nri}, payload type: {pl_type}, len payload: {len(payload)}')

        if pl_type == 28:  # FU-A (Fragmented Unit)
            fu_header = struct.unpack('!B', payload[1:2])[0]
            start_bit = (fu_header & 0x80) >> 7
            end_bit = (fu_header & 0x40) >> 6
            pl_type = fu_header & 0x1F

            if start_bit:
                # 재구성된 NAL 헤더: 원래 FU indicator의 상위 3비트와 FU header의 하위 5비트
                reconstructed_header = bytes([(nal_header & 0xE0) | pl_type])
                self.fu_buffer = [reconstructed_header + payload[2:]]
            else:
                self.fu_buffer.append(payload[2:])

            if end_bit:
                full_payload = b''.join(self.fu_buffer)
                self.fu_buffer.clear()
                self.packet_buffer.append(b'\x00\x00\x00\x01' + full_payload)

            print(f'type:{pl_type}, start bit: {start_bit}, end bit: {end_bit}')

            return

        if pl_type == 9:  # AUD (무시)
            res = b''.join(self.packet_buffer)
            self.packet_buffer.clear()
            self.packet_buffer.append(b'\x00\x00\x00\x01' + payload)
            return res

        elif pl_type == 7:
            self.sps = b'\x00\x00\x00\x01' + payload
            print("save SPS")
        elif pl_type == 8:
            self.pps = b'\x00\x00\x00\x01' + payload
            print("save PPS")

        elif pl_type == 1 or pl_type == 5:  # Non-IDR Frame
            if pl_type == 5 and self.sps and self.pps:
                self.packet_buffer.append(self.sps)
                self.packet_buffer.append(self.pps)
            self.packet_buffer.append(b'\x00\x00\x00\x01' + payload)



    def decode_h264(self, data):
        # """
        # H.264 데이터를 디코딩하여 OpenCV 프레임 생성
        # """
        # # H.264 데이터 -> NumPy 배열
        # np_array = np.frombuffer(h264_data, np.uint8)
        # # OpenCV에서 디코딩
        # frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        # return frame

        newpacket = av.Packet(data)
        frame = self.codec.decode(newpacket)[0]
        print(frame)

        img = frame.to_ndarray(format='bgr24')
        cv2.imwrite(f"./RTP_Video.jpg", img)

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
    rtp_decoder = RTPStreamDecoder(host="127.0.0.1", port=5000)
    rtp_decoder.start()