import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

def on_rtp_packet(src, packet):
    """
    RTP 패킷의 타임스탬프와 시퀀스 번호 추출
    """
    # RTP 헤더 분석
    buffer = packet.get_buffer()
    rtp_header = Gst.RTPBuffer.map(buffer, Gst.MapFlags.READ)
    if rtp_header:
        # 타임스탬프 추출
        timestamp = Gst.RTPBuffer.get_timestamp(buffer)
        # 시퀀스 번호 추출
        sequence_number = Gst.RTPBuffer.get_seq(buffer)
        print(f"Timestamp: {timestamp}, Sequence Number: {sequence_number}")
        Gst.RTPBuffer.unmap(buffer)

def gstreamer_receive_rtp():
    """
    GStreamer 파이프라인에서 RTP 패킷 처리
    """
    Gst.init(None)

    # RTP 스트림을 수신하고 디코딩하는 GStreamer 파이프라인
    pipeline = Gst.parse_launch(
        "udpsrc port=5000 caps=\"application/x-rtp, media=video, encoding-name=H264, payload=96\" ! "
        "rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
    )

    # udpsrc 요소 가져오기
    udpsrc = pipeline.get_by_name("udpsrc0")  # 기본 이름이 "udpsrc0"
    if not udpsrc:
        print("Failed to retrieve udpsrc")
        return

    # RTP 패킷 처리 신호 연결
    udpsrc.connect("handoff", on_rtp_packet)

    # GStreamer 파이프라인 실행
    pipeline.set_state(Gst.State.PLAYING)

    # GLib 이벤트 루프 실행
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("Exiting...")
        pipeline.set_state(Gst.State.NULL)

# 실행
if __name__ == "__main__":
    gstreamer_receive_rtp()
