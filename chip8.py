import pygame
import random
import struct
import sys

class AddressOutOfRange(Exception):
  pass

class ProgramCounterOutOfRange(Exception):
  pass

class StackPointerOutOfRange(Exception):
  pass

class UnsupportedOpcode(Exception):
  pass

class AddressValueIsNotEven(Exception):
  pass

class Cpu:

  font_set = (
      0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
      0x20, 0x60, 0x20, 0x20, 0x70, # 1
      0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
      0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3

      0x90, 0x90, 0xF0, 0x10, 0x10, # 4
      0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
      0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
      0xF0, 0x10, 0x20, 0x40, 0x40, # 7

      0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
      0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
      0xF0, 0x90, 0xF0, 0x90, 0x90, # A
      0xE0, 0x90, 0xE0, 0x90, 0xE0, # B

      0xF0, 0x80, 0x80, 0x80, 0xF0, # C
      0xF0, 0x80, 0x80, 0x80, 0xF0, # D
      0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
      0xF0, 0x80, 0xF0, 0x80, 0x80  # F
  ) 

  cols = 64
  rows = 32

  def __init__(self):
    self._main_optbl = {
      0x0 : self._op0_nest,
      0x1 : self._op_jmp,
      0x2 : self._op_call,
      0x3 : self._op_ske,
      0x4 : self._op_skne,
      0x5 : self._op_sker,
      0x6 : self._op_ld,
      0x7 : self._op_add,
      0x8 : self._op8_nest,
      0x9 : self._op_sner,
      0xA : self._op_ldi,
      0xB : self._op_jmpv0,
      0xC : self._op_rnd,
      0xD : self._op_drw,
      0xE : self._opE_nest,
      0xF : self._opF_nest,
    }

    self._optbl0 = {
      0xE0 : self._op_cls,
      0xEE : self._op_ret,
    }

    self._optbl8 = {
      0x0 : self._op_ldr,
      0x1 : self._op_orr,
      0x2 : self._op_andr,
      0x3 : self._op_xorr,
      0x4 : self._op_addr,
      0x5 : self._op_subr,
      0x6 : self._op_shr,
      0x7 : self._op_subnr,
      0xE : self._op_shl,
    }

    self._optblE = {
      0x9E : self._op_skp,
      0xA1 : self._op_sknp,
    }

    self._optblF = {
      0x07 : self._op_ldv,
      0x0A : self._op_ldvk,
      0x15 : self._op_lddt,
      0x18 : self._op_ldst,
      0x1E : self._op_addi,
      0x29 : self._op_ldf,
      0x33 : self._op_ldb,
      0x55 : self._op_ldix,
      0x65 : self._op_ldxi,
    }

    self.reset()

  def _unsupported_opcode(self):
    raise UnsupportedOpcode

  def _pop(self):
    if self.sp <= -1:
      raise StackPointerOutOfRange
    item = self.stack[self.sp]
    self.sp -= 1
    return item

  def _push(self, item):
    if self.sp >= len(self.stack):
      raise StackPointerOutOfRange
    self.sp += 1
    self.stack[self.sp] = item

  def _opF_nest(self):
    self._optblF.setdefault(self._nn, self._unsupported_opcode)()

  def _op_ldxi(self):
    ''' 0xFx65 - LD Vx, [I] - Read registers V0 through Vx from memory
    starting at location I. '''
    # Read values from memory starting at location I into registers V0
    # through Vx.
    for i in range(self._x + 1):
      self.V[i] = self.read(self.I + i)

  def _op_ldix(self):
    ''' 0xFx55 - LD [I], Vx - Store registers V0 through Vx in memory
    starting at location I. '''
    # Copy values of registers V0 through Vx into memory,
    # starting at the address in I.
    for i in range(self._x + 1):
      self.write(self.V[i], self.I + i)

  def _op_ldb(self):
    # 0xFx33 - LD B, Vx - Store BCD representation of Vx in memory
    # locations I, I + 1, and I + 2.
    # Takes the decimal value of Vx, and places the hundreds
    # digit in memory at location in I, the tens digit at location in I + 1,
    # and the ones digit a location I + 2.
    hundreds = self.V[self._x] // 100 # Integer division.
    tens = (self.V[self._x] - hundreds*100) // 10 # Integer division.
    ones = self.V[self._x] - hundreds*100 - tens*10
    self.memory[self.I] = hundreds
    self.memory[self.I + 1] = tens
    self.memory[self.I + 2] = ones

  def _op_ldf(self):
    # 0xFx29 - LD F, Vx - Set I = location of sprite for digit Vx. In
    # other words I will contain the address of the font character stored
    # in Vx.
    # The value of I is set to the location for the hexadecimal sprite
    # corresponding to the value of Vx.

    # Make sure that Vx is not greater than 15
    self.I = (self.V[self._x] % 16) * 5

  def _op_addi(self):
    # 0xFx1E - Set I = I + Vx.
    # The values of I and Vx are added, and the result is stored in I.
    self.I = (self.I + self.V[self._x]) & 0xFFFF

  def _op_ldst(self):
    # 0xFx18 - Set sound timer = Vx.
    # ST is set equal to the value of Vx.
    self.sound_timer = self.V[self._x]

  def _op_lddt(self):
    # 0xFx15 - Set delay timer = Vx.
    # DT is set equal to the value of Vx.
    self.delay_timer = self.V[self._x]

  def _op_ldvk(self):
    # 0xFx0A - Wait for a key press, store the value of the key in Vx
    # All execution stops until a key is pressed, then the value of that key is
    # stored in Vx.

    # Check for a keypress.
    for i in range(len(self.keyboard)):
      if self.keyboard[i]:
        self.V[self._x] = i
        break;

    # When we get out of the loop above there are two possibilities:
    # 1. The key was pressed, meaning that i is the index into the keyboard
    # list indicating a given key was pressed. In this case everthing
    # that needs to be done was already done.
    # 2. The key was not pressed, meaning that i will be equal to the
    # len(self.keyboard)-1. In this case we need to change the program
    # counter back to its original value and stop all execution.
    if not self.keyboard[i]:
      self.pc = self.pc - 2
      return # Stop all execution.

  def _op_ldv(self):
      # 0xFx07 - LD Vx, DT, Set Vx = delay timer value.
      # The value of DT is placed into Vx.
      self.V[self._x] = self.delay_timer

  def _opE_nest(self):
    self._optblE.setdefault(self._nn, self._unsupported_opcode)()

  def _op_sknp(self):
    # 0xEx9E - SKNP Vx - Skip next instruction if the key with the value of Vx is not pressed.
    # Checksthe keyboard, and if the key corresponding to the value of Vx is currently
    # in the up position, PC is incremented by 2.
    if not self.keyboard[self.V[self._x] % len(self.keyboard)]:
      self.pc = self.pc + 2

  def _op_skp(self):
    # 0xEx9E - SKP Vx - Skip next instruction if the key with the value of Vx is pressed.
    # Checksthe keyboard, and if the key corresponding to the value of Vx is currently
    # in the down position, PC is incremented by 2.
    if self.keyboard[self.V[self._x] % len(self.keyboard)]:
      self.pc = self.pc + 2

  def _op_drw(self):
    # 0xDxyn - DRW Vx, Vy, nibble - Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision
    # The interpreter reads n bytes from memory, starting at the address stored in I. These bytes are then displayed
    # as sprites on screen at coordinates (Vx, Vy). Sprites are XORed onto the existing screen.
    # If this causes any pixels to be erased, VF is set to 1, otherwise it is set to 0. 
    # If the sprite is positioned so part of it is outside the coordinates of the display, it wrraps
    # around to the oposite side of the screen. Each bit corresponds to a single pixel.
    self.draw_flag = True # Let the outside world know that display needs to be updated.
    self.V[0xF] = 0
    for yline in range(self._n):
      byte = self.read(self.I + yline)
      for xline in range(8):
        pixel = byte & (0x80 >> xline)
        if 0 != pixel:
          if(1 == self.gfx[(self.V[self._y] + yline) % self.rows][(self.V[self._x] + xline) % self.cols]):
            self.V[0xF] = 1
          self.gfx[(self.V[self._y] + yline) % self.rows][(self.V[self._x] + xline) % self.cols] ^= 1

  def _op_rnd(self):
    # 0xCxkk - RND Vx, byte - Set Vx = random byte AND kk.
    # The interpreter generates a random number from 0 to 255, which is 
    # then ANDed with the value kk. The results are stored in Vx.
    random.seed()
    self.V[self._x] = random.randrange(0x100)

    # Check if we are in the test mode and store a copy of V[x] in the 
    # V[x + 1].
    if self.test:
      self.V[(self._x + 1) % len(self.V)] = self.V[self._x] 
    self.V[self._x] &= self._nn

  def _op_jmpv0(self):
    # 0xBnnn - JP V0, addr - Jump to location nnn + V0. 
    # The program counter is set to nnn plus the value of V0.
    self.pc = self.V[0x0] + self._nnn


  def _op_ldi(self):
    # 0xAnnn - LD I, addr - Set I = nnn. 
    # The value of register I is set to nnn.
    self.I = self._nnn 

  def _op_sner(self):
    # 0x9xy0 - SNE Vx, Vy - Skip next instruction if Vx != Vy.
    if self.V[self._x] != self.V[self._y]:
      self.pc = self.pc + 2

  def _op8_nest(self):
    self._optbl8.setdefault(self._n, self._unsupported_opcode)()

  def _op_shl(self):
    # 0x8xyE - SHL Vx - Shift Vx left by one. Store most significant bit in VF
    self.V[0xF] = self.V[self._x] & 0x80
    self.V[self._x] = (self.V[self._x] << 1) & 0xFF

  def _op_subnr(self):
    # 0x8xy7 - SUBN Vx, Vy - Subract Vx from Vy. Store result in Vx. If Vx > Vy, then set VF to 1.
    self.V[0xF] = 0
    if self.V[self._y] > self.V[self._x]:
      self.V[0xF] = 1
    self.V[self._x] = self.V[self._y] - self.V[self._x]
    self.V[self._x] &= 0xFF

  def _op_shr(self):
    # 0x8xy6 - SHR Vx - Shift Vx right by one. Store least significant bit in VF
    self.V[0xF] = self.V[self._x] & 0x01
    self.V[self._x] = self.V[self._x] >> 1

  def _op_subr(self):
    # 0x8xy5 - Sub Vx, Vy - Subract Vy from Vx. Store result in Vx. If Vx > Vy, then set VF to 1.
    self.V[0xF] = 0
    if self.V[self._x] > self.V[self._y]:
      self.V[0xF] = 1
    self.V[self._x] -= self.V[self._y]
    self.V[self._x] &= 0xFF

  def _op_addr(self):
    # 0x8xy4 - Add Vx, Vy - Add reigisters Vx and Vy. Store result in Vx. If result is > 255, then set VF to 1.
    self.V[self._x] += self.V[self._y]
    self.V[0xF] = 0
    if self.V[self._x] > 0xFF:
      self.V[0xF] = 1
      self.V[self._x] &= 0xFF

  def _op_xorr(self):
      # 0x8xy3 - XOR Vx, Vy - XOR of reigisters Vx and Vy. Store result in Vx.
      self.V[self._x] ^= self.V[self._y]

  def _op_andr(self):
    # 0x8xy2 - AND Vx, Vy - Bitwise and of reigisters Vx and Vy. Store result in Vx.
    self.V[self._x] &= self.V[self._y]

  def _op_orr(self):
    # 0x8xy1 - OR Vx, Vy - Bitwise or of reigisters Vx and Vy. Store result in Vx.
    self.V[self._x] |= self.V[self._y]

  def _op_ldr(self):
    # 0x8xy0 - LD Vx, Vy - Store value of register Vy in register Vx.
    self.V[self._x] = self.V[self._y]

  def _op_add(self):
      # 7xkk - Add Vx, byte - Adds the value kk to the value of register Vx, 
      # then stores the result in Vx. 
      self.V[self._x] = (self.V[self._x] + self._nn) & 0xFF

  def _op_ld(self):
    # 0x6xkk - LD Vx, byte - Put the value kk into register Vx.
    self.V[self._x] = self._nn

  def _op_sker(self):
    # 5xy0 - SE Vx, Vy Skip next instruction if Vx = Vy.
    # Compare register Vx to register Vy, and if they are equal, 
    # increments the program counter by 2.
    if self.V[self._x] == self.V[self._y]:
      # Skip next instruction and go to the one after it.
      self.pc = self.pc + 2

  def _op_skne(self):
    # 0x4xkk - SNE Vx, byte - Skip next instruction if Vx != kk.
    # Compare Vx to kk, and if they are not equal, increment the program counter 
    # by 2.
    if self.V[self._x] != self._nn:
      # Skip next instruction and go to the one after it.
      self.pc = self.pc + 2

  def _op_ske(self):
    # 0x3xkk - SE Vx, byte - Skip next instruction if Vx = kk.
    # Compare Vx to kk, and if they are equal, increment the program counter 
    # by 2.
    if self.V[self._x] == self._nn:
      # Skip next instruction and go to the one after it.
      self.pc = self.pc + 2

  def _op_call(self):
    # 0x2nnn - CALL addr - call subroutine at nnn.
    # Increment the stack pointer, then put the current PC on the top of
    # the stack. The PC is then set to nnn.
    self._push(self.pc)
    self.pc = self._nnn

  def _op_jmp(self):
    # 0x1nnn - JP addr - jump to location nnn.
    # Set the program counter to nnn.
    self.pc = self._nnn

  def _op0_nest(self):
    self._optbl0.setdefault(self._nn, self._unsupported_opcode)()

  def _op_ret(self):
    # Return from a subroutine.
    self.pc = self._pop()

  def _op_cls(self):
    # Clear the display.
    self.gfx = [[0 for col in range(self.cols)] for row in range(self.rows)]


  def __str__(self):
    mystr = 'pc = 0x{:04X}'.format(self.pc)
    mystr = '{}{}memory[0x{:04X}] = 0x{:02X} memory[0x{:04X}] = 0x{:02X}'.format(
        mystr, ' '*3, self.pc, self.memory[self.pc], self.pc + 1, self.memory[self.pc + 1])
    mystr = '{}\nI  = 0x{:04X}'.format(mystr, self.I)
    mystr = '{}\n'.format(mystr)
    mystr = '{}{}'.format(mystr, ' '*5)
    for i in reversed(range(len(self.V))):
      mystr = '{}{:^4X}|'.format(mystr, i)
    mystr = '{}\n'.format(mystr)
    mystr = '{}V    '.format(mystr)

    for i in reversed(range(len(self.V))):
      mystr = '{}0x{:>02X}|'.format(mystr, self.V[i])

    mystr = '{}\nsp = {}'.format(mystr, self.sp)
    mystr = '{}{}Stack'.format(mystr, ' '*5)

    for i in reversed(range(len(self.stack))):
      mystr = '{}\n{}-- ------\n{}{:>2d}|0x{:04X}'.format(mystr, ' '*12, ' '*12, i, self.stack[i])

    return mystr

  def reset(self):
    self.pc = 0x200 # Program starts at 0x200
    self.I = 0x0000 # Reset index register.
    self.sp = -1 # Reset stack pointer.
    self.test = False # Is the chip in the test mode?
    self.draw_flag = False

    # Reset the keypad. If keypad[x] is True then key x is pressed, otherwise key x is not pressed.
    self.keyboard = [False] * 16

    # Clear display
    self.gfx = [[0 for col in range(type(self).cols)] for row in range(type(self).rows)]

    # Clear stack
    self.stack = [0] * 16

    # Clear registers V0-VF
    self.V = [0] * 16

    # Clear memory
    self.memory = [0] * 4096 

    # Reset timers.
    self.delay_timer = 0x0
    self.sound_timer = 0x0

    # Load font set.
    self.memory[0:80] = type(self).font_set[0:80]

  def load_app(self, file_name):
    self.reset()
    with open(file_name, 'rb') as f:
      # Read one byte at a time.
      i = 0
      byte = f.read(1)
      while byte:
        # Copy each byte into chip8 memory.
        # self.write(int.from_bytes(byte, byteorder ='little'), 0x200 + i)
        self.write(struct.unpack('B', byte)[0], 0x200 + i)
        byte = f.read(1)
        i = i + 1

  def emulate_cycle(self):
    # Check the program counter.
    if self.pc >= len(self.memory):
      raise ProgramCounterOutOfRange('pc = {}'.format(self.pc))

    # Check the stack pointer.
    if self.sp < -1 or self.sp >= len(self.stack):
      raise StackPointerOutOfRange('sp = {}'.format(self.spdefaultdict))

    self.draw_flag = False

    # Update timers
    if self.delay_timer > 0:
      self.delay_timer = self.delay_timer - 1

    if self.sound_timer > 0:
      # NOTE: make a sound.
      self.sound_timer = self.sound_timer - 1

    # Fetch opcode
    opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]

    # Update program counter.
    self.pc = self.pc + 2

    # Decode.
    self._nnn = opcode & 0x0FFF
    self._nn  = opcode & 0x00FF
    self._n   = opcode & 0x000F
    self._x   = (opcode & 0x0F00) >> 8
    self._y   = (opcode & 0x00F0) >> 4

    # Execute.
    self._main_optbl.setdefault((opcode & 0xF000) >> 12, self._unsupported_opcode)()

  def print_gfx(self):
    for row in range(self.rows):
      print('{:2}'.format(row), end=': ')
      for col in range(self.cols):
        if self.gfx[row][col]:
          print('*', end='')
        else:
          print(' ', end='')
      print()

  def write_opcode(self, opcode, addr):
    # Make sure opcode is 2 bytes.
    opcode = opcode & 0xFFFF

    # Make sure address is in the 4KB range.
    addr = addr & 0xFFF

    # Make sure that address is even.
    if 0 != addr % 2:
      raise AddressValueIsNotEven('addr = {}'.format(addr))

    if addr < 0x200:
      raise AddressOutOfRange('addr = {}'.format(addr))

    self.memory[addr] = (opcode & 0xFF00) >> 8
    self.memory[addr+1] = (opcode & 0xFF)

  def write(self, byte, addr):
    # Make sure address is in the 4KB range.
    addr = addr & 0xFFF
    self.memory[addr] = byte

  def read_opcode(self, addr):
    # Make sure address is in the 4KB range.
    addr = addr & 0xFFF

    # Make sure that address is even.
    if 0 != addr % 2:
      raise AddressValueIsNotEven('addr = {}'.format(addr))

    return (self.memory[addr] << 8) | (self.memory[addr+1])

  def read(self, addr):
    # Make sure address is in the 4KB range.
    return self.memory[addr & 0xFFF]

  def clear_memory(self):
    self.memory[0x200:len(self.memory)] = [0] * (len(self.memory) - 0x200)

class Block(pygame.sprite.Sprite):
  def __init__(self, row, col, gfx):
    pygame.sprite.Sprite.__init__(self)
    self.image = pygame.Surface((10, 10)).convert()
    self.image.fill((255, 255, 255))
    self.rect = self.image.get_rect()
    self.rect.left = col*10
    self.rect.top = row*10
    self.row = row
    self.col = col
    self.gfx = gfx

  def update(self):
    if self.gfx[self.row][self.col]:
      self.image.fill((255, 255, 255))
    else:
      self.image.fill((0, 0, 0))

class Emulator:
  def __init__(self):
    self._cpu = Cpu()

  def _press_key(self, key, keyboard, is_down):
    if pygame.K_1 == key:
      self._cpu.keyboard[0x1] = is_down
    elif pygame.K_2 == key:
      self._cpu.keyboard[0x2] = is_down
    elif pygame.K_3 == key:
      self._cpu.keyboard[0x3] = is_down
    elif pygame.K_4 == key:
      self._cpu.keyboard[0xC] = is_down
    elif pygame.K_q == key:
      self._cpu.keyboard[0x4] = is_down
    elif pygame.K_w == key:
      self._cpu.keyboard[0x5] = is_down
    elif pygame.K_e == key:
      self._cpu.keyboard[0x6] = is_down
    elif pygame.K_r == key:
      self._cpu.keyboard[0xD] = is_down
    elif pygame.K_a == key:
      self._cpu.keyboard[0x7] = is_down
    elif pygame.K_s == key:
      self._cpu.keyboard[0x8] = is_down
    elif pygame.K_d == key:
      self._cpu.keyboard[0x9] = is_down
    elif pygame.K_f == key:
      self._cpu.keyboard[0xE] = is_down
    elif pygame.K_z == key:
      self._cpu.keyboard[0xA] = is_down
    elif pygame.K_x == key:
      self._cpu.keyboard[0x0] = is_down
    elif pygame.K_c == key:
      self._cpu.keyboard[0xB] = is_down
    elif pygame.K_v == key:
      self._cpu.keyboard[0xF] = is_down

  def load_app(self, file_name):
    self._cpu.load_app(file_name)

  def run(self):
    # I - Initialize.
    pygame.init()

    # D - Display.
    display = pygame.display.set_mode((640, 320))

    # E - Entities.
    background = pygame.Surface(display.get_size())
    background.fill((0, 0, 0))
    background = background.convert()
    all_sprites = pygame.sprite.Group()
    for row in range(self._cpu.rows):
      for col in range(self._cpu.cols):
        all_sprites.add(Block(row, col, self._cpu.gfx))

    # A - Action.
    clock = pygame.time.Clock()
    keep_going = True

    # A - Assign values.
    # L - Loop.
    while keep_going:

      # T - Timing.
      clock.tick(60) # 60 Frames per second.

      self._cpu.emulate_cycle()

      # E - Events.
      for event in pygame.event.get():
        if pygame.QUIT == event.type:
          keep_going = False
        elif pygame.KEYDOWN == event.type:
          self._press_key(event.key, self._cpu.keyboard, True)
        elif pygame.KEYUP == event.type:
          self._press_key(event.key, self._cpu.keyboard, False)

      # R - Refresh display.
      if self._cpu.draw_flag:
        all_sprites.clear(display, background)
        all_sprites.update()
        all_sprites.draw(display)
        pygame.display.flip()

def main():
  usage = '{} <file name>'.format(__file__)
  if 2 != len(sys.argv):
    print(usage)
    sys.exit()
  emulator = Emulator()
  emulator.load_app(sys.argv[1])
  emulator.run()

if '__main__' == __name__:
  main()
