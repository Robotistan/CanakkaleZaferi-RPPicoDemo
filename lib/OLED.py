##########SSD1306 Library##########
set_contrast = const(0x81)
set_entire_on = const(0xA4)
set_norm_inv = const(0xA6)
set_disp = const(0xAE)
set_mem_addr = const(0x20)
set_color_addr = const(0x21)
set_page_addr = const(0x22)
set_disp_start_line = const(0x40)
set_seg_remap = const(0xA0)
set_mux_ratio = const(0xA8)
set_com_out_dir = const(0xC0)
set_disp_offset = const(0xD3)
set_com_pin_cfg = const(0xDA)
set_disp_clk_div = const(0xD5)
set_precharge = const(0xD9)
set_vcom_desel = const(0xDB)
set_charge_pump = const(0x8D)

# Subclassing FrameBuffer provides support for graphics primitives
# http://docs.micropython.org/en/latest/pyboard/library/framebuf.html
class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def init_display(self):
        for cmd in (
            set_disp | 0x00,  # off
            # address setting
            set_mem_addr,
            0x00,  # horizontal
            # resolution and layout
            set_disp_start_line | 0x00,
            set_seg_remap |0x001, # column addr 127 mapped to SEG0
            set_mux_ratio,
            self.height - 1,
            set_com_out_dir | 0x08,  # scan from COM[N] to COM0
            set_disp_offset,
            0x00,
            set_com_pin_cfg,
            0x02 if self.width > 2 * self.height else 0x12,
            # timing and driving scheme
            set_disp_clk_div,
            0x80,
            set_precharge,
            0x22 if self.external_vcc else 0xF1,
            set_vcom_desel,
            0x30,  # 0.83*Vcc
            # display
            set_contrast,
            0xFF,  # maximum
            set_entire_on,  # output follows RAM contents
            set_norm_inv,  # not inverted
            # charge pump
            set_charge_pump,
            0x10 if self.external_vcc else 0x14,
            set_disp | 0x01,
        ):  # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        self.write_cmd(set_disp | 0x00)

    def poweron(self):
        self.write_cmd(set_disp | 0x01)

    def contrast(self, contrast):
        self.write_cmd(set_contrast)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(set_norm_inv | (invert & 1))

    def show(self):
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            # displays with width of 64 pixels are shifted by 32
            x0 += 32
            x1 += 32
        self.write_cmd(set_color_addr)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(set_page_addr)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)


class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.write_list = [b"\x40", None]  # Co=0, D/C#=1
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)
        