## send
gst-launch-1.0 videotestsrc ! videoconvert ! x264enc tune=zerolatency ! rtph264pay config-interval=1 ! udpsink host=127.0.0.1 port=5000

## show get image
ffplay -protocol_whitelist file,udp,rtp -i stream.sdp

## get pts
ffmpeg -protocol_whitelist file,udp,rtp -copyts -i stream.sdp -vf showinfo -max_delay 500000 -y output.mp4
