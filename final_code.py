import socket
import struct
import av

import cv2

class RTPStreamDecoder:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.packet_buffer = []
        self.fu_buffer = []
        self.sps = None
        self.pps = None 
        self.timestamp = None

        self.codec = av.CodecContext.create('h264', 'r')

    def start(self):
        # UDP 소켓 생성 및 바인딩
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print(f"Listening for RTP packets on {self.host}:{self.port}")

        while True:
            data, addr = sock.recvfrom(4096)

            if len(data) >= 12:
                timestamp = self.parse_timestamp(data)
                frm = self.process_payload(data)
                if frm is not None and len(frm) > 0 and self.sps and self.pps:
                    img = self.decode_h264(frm)

                    cv2.imwrite(f"./RTP_Video.jpg", img)
                
                self.timestamp = timestamp

    def parse_timestamp(self, data):
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

        return timestamp

    def process_payload(self, data):
        payload = data[12:]
        nal_header = struct.unpack('!B', payload[0:1])[0]

        f = nal_header >> 7
        nri = (nal_header & 0x60) >> 5
        pl_type = nal_header & 0x1F

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
        newpacket = av.Packet(data)
        frame = self.codec.decode(newpacket)[0]

        img = frame.to_ndarray(format='bgr24')

        return img
        

if __name__ == "__main__":
    rtp_decoder = RTPStreamDecoder(host="127.0.0.1", port=5000)
    rtp_decoder.start()