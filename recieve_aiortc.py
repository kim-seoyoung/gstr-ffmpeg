import asyncio
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
from av import VideoFrame

async def receive_rtp_stream():
    # RTP 스트림을 특정 IP:PORT에서 받기 위해 MediaPlayer 사용
    player = MediaPlayer("/home/seoyoung/Downloads/stream.sdp", format="sdp"
                         , options={"protocol_whitelist": "file,rtp,udp"})

    while True:
        frame = await player.video.recv()

        if frame is None:
            continue

        # 타임스탬프 추출
        timestamp = frame.pts  # PTS 기반 타임스탬프
        img = frame.to_ndarray(format="bgr24")
        print(img.shape)

        print(f"Frame Timestamp: {timestamp}")
        cv2.imwrite("RTP_Video.jpg", img)
        # k = cv2.waitKey(1) 

        # if k == ord('q'):
        #     break

        # # asyncio 루프와 충돌 방지
        # await asyncio.sleep(0.01)

    player.stop()
    cv2.destroyAllWindows()

if __name__ == '__main__':

    # asyncio 실행
    asyncio.run(receive_rtp_stream())
