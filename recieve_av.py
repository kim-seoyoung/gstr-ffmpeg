import io
import socket
import av

class RTPUDPReceiver:
    def __init__(self, ip, port):
        """
        UDP로 RTP 비디오 스트림을 수신하는 클래스
        :param ip: 수신할 IP 주소 (기본값: 모든 인터페이스)
        :param port: 수신할 포트
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        print(f"Listening for RTP packets on {ip}:{port}...")

        # RTP 데이터를 저장할 버퍼
        self.raw_data = io.BytesIO()
        self.container = av.open(self.raw_data, format="h264", mode="r")
        self.cur_pos = 0
        self.frames = []

        self.current_frame = b''
        self.packet_buffer = []
        self.sps_pps = []

    def has_sps_pps(self):
        """
        SPS & PPS가 수신되었는지 확인
        """
        return len(self.sps_pps) > 0
    
    def handle_payload(self, payload):
        """
        RTP 페이로드 처리 및 NAL 조립
        """

        nal_type = payload[0] & 0x1F  # NAL 유형 추출
        print(f'nal type: {nal_type}')

        if nal_type == 9:  # AUD (무시)
            if not self.has_sps_pps():
                return
            if self.packet_buffer:
                nal_data = b''.join(self.packet_buffer)
                self.decode_h264(nal_data)
            self.packet_buffer = []
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
            # self.packet_buffer.append(b'\x00\x00\x00\x01' + payload)
            self.decode_h264(payload)
            self.sps_pps.append(payload)

        elif nal_type == 1 or nal_type == 5:  # Non-IDR Frame
            if not self.has_sps_pps():
                print("Skipping P-Frame: SPS/PPS missing!")
                return
            # self.packet_buffer.append(b'\x00\x00\x00\x01' + payload)
            self.decode_h264(payload)
            self.sps_pps.append(payload)

    def decode_h264(self, rtp_payload):
        # RTP 데이터 버퍼에 쓰기
        self.raw_data.write(rtp_payload)  # RTP 헤더(12바이트) 제외
        self.raw_data.seek(self.cur_pos)

        try:
            for packet in self.container.demux():
                if packet.size == 0:
                    continue

                print(packet)

                self.cur_pos += packet.size  # 읽은 위치 업데이트

                # 패킷에서 PTS(프레젠테이션 타임스탬프) 추출
                print(f"Packet PTS: {packet.pts}")

                # 패킷을 디코딩하여 프레임 추출
                for frame in packet.decode():
                    self.frames.append(frame)
                    print(f"Decoded Frame PTS: {frame.pts}")

        except av.AVError as e:
            print(f"Decoding Error: {e}")


    def receive_rtp_packet(self):
        """
        UDP 소켓을 통해 RTP 패킷을 수신하고, pyav로 디코딩한다.
        """
        while True:
            # RTP 패킷 수신 (MTU 크기 제한: 1500바이트)
            rtp_payload, addr = self.sock.recvfrom(2048)
            timestamp = int.from_bytes(rtp_payload[4:8], byteorder="big")  # RTP 타임스탬프 추출

            print(f"Received RTP Packet from {addr} with Timestamp: {timestamp}")

            self.handle_payload(rtp_payload[12:])
            

# UDP RTP 수신기 실행
receiver = RTPUDPReceiver(ip="127.0.0.1", port=5000)
receiver.receive_rtp_packet()
