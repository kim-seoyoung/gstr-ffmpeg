import subprocess
import numpy as np
import cv2

def receive_rtp_video_with_timestamps():
    width, height = 320, 240
    frame_size = width * height * 3

    command = [
        'ffmpeg',
        '-protocol_whitelist', 'file,udp,rtp',
        '-fflags', 'nobuffer',
    '-flags', 'low_delay',
    '-analyzeduration', '0',
        '-i', '/home/seoyoung/Downloads/stream.sdp',
        '-vf', 'showinfo',
        '-pix_fmt', 'rgb24',
        '-f', 'rawvideo',
        'pipe:1'
    ]

    # FFmpeg 프로세스 실행
    process = subprocess.Popen(command, stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, bufsize=10**8)

    print('start')
    while True:
        # 파이프에서 프레임 데이터 읽기
        frame_data = process.stdout.read(frame_size)
        if not frame_data:
            break

        # NumPy 배열로 변환
        frame = np.frombuffer(frame_data, np.uint8).reshape((height, width, 3))

        # stderr에서 타임스탬프 로그 읽기
        while True:
            line = process.stderr.readline().decode('utf-8')
            if 'pts_time' in line:
                print(f"Timestamp Info: {line.strip()}")
                break

        # OpenCV로 프레임 표시
        cv2.imshow('RTP Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    process.stdout.close()
    process.stderr.close()
    process.wait()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    # 실행
    receive_rtp_video_with_timestamps()
