# Read-only: samples each RK3566 GPIO bank input register (EXT_PORT, 0x70) via /dev/mem and logs any pin that changes.
import mmap, os, struct, time, sys
BANKS = {0: 0xfdd60000, 1: 0xfe740000, 2: 0xfe750000, 3: 0xfe760000, 4: 0xfe770000}
fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
maps = {b: mmap.mmap(fd, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ, offset=a) for b, a in BANKS.items()}
rd = lambda b: struct.unpack_from("<I", maps[b], 0x70)[0]
name = lambda b, n: "gpio%d-%s%d (line %d)" % (b, "ABCD"[n // 8], n % 8, n)
prev = {b: rd(b) for b in BANKS}
noisy = set()
t0 = time.time()
while time.time() - t0 < 3:                     # 3 s baseline: pins that move on their own are flagged noisy
    for b in BANKS:
        v = rd(b); d = v ^ prev[b]
        for n in range(32):
            if d >> n & 1: noisy.add((b, n))
        prev[b] = v
    time.sleep(0.02)
print("baseline done; noisy pins ignored:", ", ".join(name(*p) for p in sorted(noisy)) or "none", flush=True)
end = time.time() + float(sys.argv[1]) if len(sys.argv) > 1 else 1e18
while time.time() < end:
    for b in BANKS:
        v = rd(b); d = v ^ prev[b]
        for n in range(32):
            if d >> n & 1 and (b, n) not in noisy:
                print("%s %s -> %d" % (time.strftime("%H:%M:%S"), name(b, n), v >> n & 1), flush=True)
        prev[b] = v
    time.sleep(0.05)
