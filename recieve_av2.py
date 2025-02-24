import av
import cv2
import numpy as np
import ctypes

def receive_rtp_stream_from_sdp(sdp_file):
    # SDP 파일을 통해 RTP 스트림을 열기
    container = av.open(
            file=sdp_file, format='sdp', mode="r", options={"protocol_whitelist": "file,rtp,udp"})

    frm_cnt = 0
    codec = av.CodecContext.create('h264', 'r')
    for packet in container.demux():
        data = ctypes.string_at(packet.buffer_ptr, packet.buffer_size)
        with open(f'./data/frm_{frm_cnt}.txt', 'wb') as f:
            f.write(data)
        newpacket = av.Packet(data)
        dd = codec.decode(newpacket)
        print(dd)
        for frame in packet.decode():
            # RTP 패킷에서 프레임 정보와 PTS를 가져오기
            if isinstance(frame, av.VideoFrame):
                timestamp = frame.pts
                print(f"Frame PTS: {timestamp}")

                # NumPy 배열로 변환하여 OpenCV로 프레임 디스플레이
                img = frame.to_ndarray(format='bgr24')
                cv2.imwrite(f"./frms/RTP_Video_{frm_cnt}.jpg", img)
                frm_cnt += 1
                # cv2.imshow('RTP Stream Frame', img)

                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break

    cv2.destroyAllWindows()

# 사용 예시
if __name__ == '__main__':
    sdp_file_path = "./stream.sdp"
    receive_rtp_stream_from_sdp(sdp_file_path)