# Logic-analyzer stimulus, 10 min: SPI1 at 1 MHz sending A5 0F x4 every 0.5 s; reset gpio149 toggles each 1 s.
import os, fcntl, struct, time
SPI_IOC_WR_MAX_SPEED_HZ = 0x40046b04
SPI_IOC_WR_MODE = 0x40016b01
fd = os.open("/dev/spidev1.0", os.O_RDWR)
fcntl.ioctl(fd, SPI_IOC_WR_MODE, struct.pack("B", 0))
fcntl.ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, struct.pack("I", 1000000))
g = "/sys/class/gpio/gpio149"
if not os.path.isdir(g):
    open("/sys/class/gpio/export", "w").write("149"); time.sleep(0.2)
open(g + "/direction", "w").write("out")
end, rst, last = time.time() + 600, 0, 0.0
while time.time() < end:
    now = time.time()
    if now - last >= 1.0:
        rst ^= 1; open(g + "/value", "w").write(str(rst)); last = now
    os.write(fd, bytes([0xA5, 0x0F] * 4))
    time.sleep(0.5)
open(g + "/value", "w").write("0"); open(g + "/direction", "w").write("in")
