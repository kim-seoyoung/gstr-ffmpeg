import ffmpeg
import numpy as np
import cv2

def receive_rtp_video_with_timestamps():
    # FFmpeg 입력 및 출력 설정
    process = (
        ffmpeg
        .input('/home/seoyoung/Downloads/stream.sdp', protocol_whitelist='file,udp,rtp')
        .output('pipe:', format='rawvideo', pix_fmt='rgb24', vf='showinfo')  # 영상 데이터를 파이프로 출력
        .run_async(pipe_stdout=True, pipe_stderr=True, pipe_stdin=True)
    )

    # 영상 프레임 크기 설정 (GStreamer 송신 설정에 따라)
    width, height = 320, 240  # GStreamer에서 설정한 해상도에 맞춤
    frame_size = width * height * 3  # RGB24 픽셀 데이터 크기

    print('start')
    # 프레임과 타임스탬프 처리 루프
    while True:
        # 영상 프레임 데이터 읽기
        frame_data = process.stdout.read(frame_size)

        if not frame_data:
            break

        # 프레임 데이터를 NumPy 배열로 변환
        frame = np.frombuffer(frame_data, np.uint8).reshape((height, width, 3))

        # FFmpeg 로그에서 타임스탬프 읽기
        while True:
            line = process.stderr.readline().decode('utf-8')

            if 'pts_time' in line:  # PTS(Time) 정보 포함된 줄 필터링
                print(f"Timestamp Info: {line.strip()}")
                break

            if not line:
                break

        # OpenCV로 프레임 표시 (원하면 주석 처리 가능)
        cv2.imshow('Video Frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 리소스 정리
    process.stdout.close()
    process.stderr.close()
    process.wait()
    cv2.destroyAllWindows()

# 실행
receive_rtp_video_with_timestamps()
