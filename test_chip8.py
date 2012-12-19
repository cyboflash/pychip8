import chip8 
import random
import sys 
import unittest

class TestChip8(unittest.TestCase):
  def setUp(self):
    self.dut = chip8.Chip8()
    self.dut.test = True

  def test_write(self):
    ''' Test write to memory with no exceptions raised.'''
    for i in range(10):
      random.seed()
      data = random.randrange(0x10000)
      addr = random.randint(0x200, 0xFFF)
      while (0 != addr % 2):
        addr = random.randint(0x200, 0xFFF)
      self.dut.write_opcode(data, addr)
      self.assertEqual(self.dut.memory[addr], (data & 0xFF00) >> 8)
      self.assertEqual(self.dut.memory[addr+1], data & 0x00FF)

  def test_write_raise_address_out_of_range(self):
    ''' Test write to raise AddressOutOfRange.'''
    for i in range(10):
      random.seed()
      data = random.randrange(0x10000)
      addr = random.randrange(0x200)
      while (0 != addr % 2):
        addr = random.randrange(0x200)

      with self.assertRaises(chip8.AddressOutOfRange):
        self.dut.write_opcode(data, addr)

  def test_write_raise_address_value_is_not_even(self):
    ''' Test write to raise AddressValueIsNotEven.'''
    for i in range(10):
      random.seed()
      data = random.randrange(0x10000)
      addr = random.randint(0x200, 0x1000)
      while (0 == addr % 2):
        addr = random.randint(0x200, 0x1000)

      with self.assertRaises(chip8.AddressValueIsNotEven):
        self.dut.write_opcode(data, addr)

  def test_read_opcode(self):
    data = []
    addr = []
    for i in range(10):
      random.seed()
      data.append(random.randrange(0x10000))
      addr.append(random.randrange(0x1000))
      while (0 != addr[i] % 2):
        random.seed()
        addr[i] = random.randrange(0x1000)

      self.dut.memory[addr[i]] = (data[i] & 0xFF00) >> 8
      self.dut.memory[addr[i]+1] = data[i] & 0x00FF

    for i in range(10):
      opcode = self.dut.read_opcode(addr[i])
      self.assertEqual(opcode, data[i])

  def test_read_opcode_address_value_is_not_even(self):
    data = []
    addr = []
    for i in range(10):
      random.seed()
      data.append(random.randrange(0x10000))
      addr.append(random.randrange(0x1000))
      while (0 == addr[i] % 2):
        random.seed()
        addr[i] = random.randrange(0x1000)

      self.dut.memory[addr[i]] = (data[i] & 0xFF00) >> 8
      self.dut.memory[addr[i]+1] = data[i] & 0x00FF

    with self.assertRaises(chip8.AddressValueIsNotEven):
      for i in range(10):
        opcode = self.dut.read_opcode(addr[i])

  def test_cls(self):
    ''' Test 0x00E0 - clear the display. '''
    # Write random data to the screen
    opcode = 0x00E0
    random.seed()
    self.dut.gfx = [[random.randint(0,1) for col in range(self.dut.cols)] for row in range(self.dut.rows)]
      
    self.dut.write_opcode(opcode, self.dut.pc)
    self.dut.emulate_cycle()
    for row in range(self.dut.rows):
      self.assertSequenceEqual(self.dut.gfx[row], [0]*self.dut.cols)

  def test_ret(self):
    ''' Test 0x00EE - return from a subroutine. '''
    # Sets the program counter to the address at the top of the stack,
    # then subracts 1 from the stack pointer
    opcode = 0x00EE
    random.seed()
    rand_addr = random.randrange(0x200, 0x1000)
    while 0 != (rand_addr % 2):
      rand_addr = random.randrange(0x200, 0x1000)

    self.dut.sp = self.dut.sp + 1
    self.dut.stack[self.dut.sp] = rand_addr
    self.dut.write_opcode(opcode, 0x200)
    self.dut.emulate_cycle()
    self.assertEqual(self.dut.pc, rand_addr)
    self.assertEqual(self.dut.sp, -1)

  def test_jp(self):
    ''' Test 0x1nnn - jump to location nnn. '''
    # The interpreter sets the program counter to nnn
    addr = random.randint(0x200, 0x1000)
    while 0 != (addr % 2):
      addr = random.randint(0x200, 0x1000)

    opcode = 0x1000 | addr
    self.dut.write_opcode(opcode, 0x200)
    self.dut.emulate_cycle()
    self.assertEqual(self.dut.pc, addr)

  def test_call(self):
    ''' Test 0x2nnn - call subroutine at nnn. '''
    # The interpreter increments the stack pointer, then puts the current PC on 
    # the top of the stack. The PC is then set to nnn
    random.seed()
    addr = random.randrange(0x200, 0x1000)
    while 0 != (addr % 2):
      addr = random.randrange(0x200, 0x1000)

    pc = random.randrange(0x200, 0x1000)
    while 0 != (pc % 2):
      pc = random.randrange(0x200, 0x1000)

    opcode = 0x2000 | addr
    self.dut.pc = pc
    self.dut.write_opcode(opcode, pc)
    self.dut.emulate_cycle()
    self.assertEqual(self.dut.sp, 0)
    self.assertEqual(self.dut.stack[self.dut.sp], pc + 2)
    self.assertEqual(self.dut.pc, addr)

  def test_sevxbyte_equal(self):
    ''' Test 0x3xkk - skip next instruction if Vx = kk. Tests for equality. '''
    # The interpreter compares register Vx to kk, and if they are equal,
    # increments the program counter by 2.

    for i in range(len(self.dut.V)):
      pc = self.dut.pc
      random.seed()
      val = random.randrange(256)
      self.dut.V[i] = val
      opcode = 0x3000 | (i << 8) | val
      self.dut.write_opcode(opcode, pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.pc, pc + 4)

  def test_sevxbyte_not_equal(self):
    ''' Test 0x3xkk - skip next instruction if Vx = kk. Tests for not equality. '''
    # The interpreter compares register Vx to kk, and if they are equal,
    # increments the program counter by 2.

    for i in range(len(self.dut.V)):
      pc = self.dut.pc
      random.seed()
      val = random.randrange(256)
      self.dut.V[i] = val + 1
      opcode = 0x3000 | (i << 8) | val
      self.dut.write_opcode(opcode, pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.pc, pc + 2)

  def test_raise_unsopported_opcode(self):
    ''' Test raising of UsupportedOpcode exception. '''
    with self.assertRaises(chip8.UnsupportedOpcode):
      self.dut.write_opcode(0x0000, 0x200)
      self.dut.emulate_cycle()

  def test_snevxbyte_not_equal(self):
    ''' Test 4xkk - Skip next instruction if Vx != kk. '''
    # The interpreter compares register Vx to kk, and if they are not equal, 
    # increments the program counter by 2.
    for i in range(len(self.dut.V)):
      pc = self.dut.pc
      random.seed()
      val = random.randrange(256)
      self.dut.V[i] = val + 1
      opcode = 0x4000 | (i << 8) | val
      self.dut.write_opcode(opcode, pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.pc, pc + 4)

  def test_snevxbyte_equal(self):
    ''' Test 4xkk - Skip next instruction if Vx != kk. '''
    # The interpreter compares register Vx to kk, and if they are not equal, 
    # increments the program counter by 2.
    for i in range(len(self.dut.V)):
      pc = self.dut.pc
      random.seed()
      val = random.randrange(256)
      self.dut.V[i] = val
      opcode = 0x4000 | (i << 8) | val
      self.dut.write_opcode(opcode, pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.pc, pc + 2)

  def test_sevxvy_equal(self):
    ''' Test 5xy0 - Skip next instruction if Vx == Vy. '''
    # The interpreter compares register Vx to Vy, and if they are equal,
    # increments the program counter by 2.
    for i in range(len(self.dut.V)):
      random.seed()
      val = random.randrange(256)
      self.dut.V[i] = val
      for j in range(i + 1, len(self.dut.V)):
        pc = self.dut.pc
        self.dut.V[j] = val
        opcode = 0x5000 | (i << 8) | (j << 4)
        self.dut.write_opcode(opcode, pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, pc + 4)

  def test_sevxvy_not_equal(self):
    ''' Test 5xy0 - Skip next instruction if Vx == Vy. '''
    # The interpreter compares register Vx to Vy, and if they are equal,
    # increments the program counter by 2.
    for i in range(len(self.dut.V)):
      random.seed()
      val = random.randrange(256)
      self.dut.V[i] = val
      for j in range(i + 1, len(self.dut.V)):
        pc = self.dut.pc
        self.dut.V[j] = val + 1
        opcode = 0x5000 | (i << 8) | (j << 4)
        self.dut.write_opcode(opcode, pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, pc + 2)

  def test_ldvxbyte(self):
    ''' Test 6xkk - Set Vx = kk. '''
    # The interpreter puts the value kk into register Vx. 
    for i in range(len(self.dut.V)):
      random.seed()
      val = random.randrange(256)
      opcode = 0x6000 | (i << 8) | val
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.V[i], val)

  def test_addvxbyte(self):
    ''' Test 7xkk - Set Vx = Vx + kk. '''
    # Adds the value kk to the value of register Vx, then stores result in Vx.
    for i in range(len(self.dut.V)):
      random.seed()
      val1 = random.randrange(256)
      val2 = random.randrange(256)
      self.dut.V[i] = val1
      opcode = 0x7000 | (i << 8) | val2
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.V[i], (val1 + val2) & 0xFF)

  def test_ldvxvy(self):
    ''' Test 8xy0 - Set Vx = Vy. '''
    # Store the value of register Vy in register Vx.
    for i in range(len(self.dut.V)):
      for j in range(i + 1, len(self.dut.V)):
        random.seed()
        opcode = 0x8000 | (i << 8) | (j << 4)
        val = random.randrange(256)
        self.dut.V[j] = val
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[i], self.dut.V[j])

  def test_orvxvy(self):
    ''' Test 8xy1 - OR Vx, Vy. '''
    # Set Vx = Vx OR Vy, bitwise or.
    for i in range(len(self.dut.V)):
      for j in range(i + 1, len(self.dut.V)):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        self.dut.V[i] = val1
        self.dut.V[j] = val2
        opcode = 0x8001 | (i << 8) | (j << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[i], val1 | val2)

  def test_andvxvy(self):
    ''' Test 8xy2 - OR Vx, Vy. '''
    # Set Vx = Vx AND Vy, bitwise AND.
    for i in range(len(self.dut.V)):
      for j in range(i + 1, len(self.dut.V)):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        self.dut.V[i] = val1
        self.dut.V[j] = val2
        opcode = 0x8002 | (i << 8) | (j << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[i], val1 & val2)

  def test_xorvxvy(self):
    ''' Test 8xy3 - XOR Vx, Vy. '''
    # Set Vx = Vx XOR Vy.
    for i in range(len(self.dut.V)):
      for j in range(i + 1, len(self.dut.V)):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        self.dut.V[i] = val1
        self.dut.V[j] = val2
        opcode = 0x8003 | (i << 8) | (j << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[i], val1 ^ val2)

  def test_addvxvy(self):
    ''' Test 8xy4 - ADD Vx, Vy. '''
    # Add Vx, Vy. Store result in Vx. Carry bit is stored in VF.
    for i in range(len(self.dut.V)):
      for j in range(i + 1, len(self.dut.V)):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        self.dut.V[i] = val1
        self.dut.V[j] = val2
        opcode = 0x8004 | (i << 8) | (j << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[i], (val1 + val2) & 0xFF)
        if val1 + val2 > 0xFF:
          self.assertEqual(self.dut.V[0xF], 1)
        else:
          self.assertEqual(self.dut.V[0xF], 0)

  def test_subvxvy(self):
    ''' Test 8xy5 - SUB Vx, Vy. '''
    # SUB Vx, Vy. Vx = Vx - Vy, VF = Not Borrow, i.e if Vx > Vy then VF = 1, otherwise VF = 0
    for i in range(len(self.dut.V)-1):
      for j in range(i + 1, len(self.dut.V)-1):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        self.dut.V[i] = val1
        self.dut.V[j] = val2
        opcode = 0x8005 | (i << 8) | (j << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[i], (val1 - val2) & 0xFF)
        if val1 > val2:
          self.assertEqual(self.dut.V[0xF], 1)
        else:
          self.assertEqual(self.dut.V[0xF], 0)

  def test_shrvx(self):
    ''' Test 8xy6 - SHR Vx - Shift Vx right by one. '''
    # SHR Vx - Set Vx = Vx SHR 1. If the least-significant bit of Vx is 1, then VF is set to 1
    # otherwise 0. Then Vx is divided by 2
    for i in range(len(self.dut.V)-1):
      random.seed()
      val1 = random.randrange(256)
      self.dut.V[i] = val1
      opcode = 0x8006 | (i << 8)
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.V[i], (val1 >> 1))
      self.assertEqual(self.dut.V[0xF], val1 & 0x01)

  def test_subnvxvy(self):
    ''' Test 8xy7 - SUBN Vx, Vy. '''
    # Set Vx = Vy - Vx, VF = Not Borrow, i.e if Vy > Vx then VF = 1, otherwise VF = 0
    for x in range(len(self.dut.V)-2):
      for y in range(x + 1, len(self.dut.V)-1):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        self.dut.V[x] = val1
        self.dut.V[y] = val2
        opcode = 0x8007 | (x << 8) | (y << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[x], (val2 - val1) & 0xFF)
        if val2 > val1:
          self.assertEqual(self.dut.V[0xF], 1)
        else:
          self.assertEqual(self.dut.V[0xF], 0)

  def test_shlvx(self):
    ''' Test 8xyE - SHL Vx - Shift Vx left by one. '''
    # SHL Vx - Set Vx = Vx SHL 1. If the most-significant bit of Vx is 1, then VF is set to 1
    # otherwise 0. Then Vx is multiplied by 2
    for i in range(len(self.dut.V)-1):
      random.seed()
      val1 = random.randrange(256)
      self.dut.V[i] = val1
      opcode = 0x800E | (i << 8)
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.V[i], (val1 << 1) & 0xFF)
      self.assertEqual(self.dut.V[0xF], val1 & 0x80)

  def test_snevxvy_not_equal(self):
    ''' Test 9xy0 - SNE Vx, Vy - Skip next instruction if Vx != Vy. '''
    # Test for not equality.
    # Compare Vx and Vy, if they are not equal increment program counter by 2.
    for x in range(len(self.dut.V)-1):
      for y in range(x + 1, len(self.dut.V)):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        while(val2 == val1):
          random.seed()
          val2 = random.randrange(256)

        self.dut.V[x] = val1
        self.dut.V[y] = val2
        opcode = 0x9000 | (x << 8) | (y << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        start_pc = self.dut.pc
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, start_pc + 4)

  def test_snevxvy_equal(self):
    ''' Test 9xy0 - SNE Vx, Vy - Skip next instruction if Vx != Vy. '''
    # Test for equality.
    # Compare Vx and Vy, if they are not equal increment program counter by 2.
    for x in range(len(self.dut.V)-1):
      for y in range(x + 1, len(self.dut.V)):
        random.seed()
        val1 = random.randrange(256)
        val2 = random.randrange(256)
        while(val2 != val1):
          random.seed()
          val2 = random.randrange(256)

        self.dut.V[x] = val1
        self.dut.V[y] = val2
        opcode = 0x9000 | (x << 8) | (y << 4)
        self.dut.write_opcode(opcode, self.dut.pc)
        start_pc = self.dut.pc
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, start_pc + 2)

  def test_ldiaddr(self):
    ''' Test 0xAnnn - LD I, addr - The value of register I is set to nnn. '''
    for i in range(10):
      random.seed()
      addr = random.randrange(0x1000)
      opcode = 0xA000 | addr
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.I, addr)

  def test_jpv0addr(self):
    ''' Test 0xBnnn - JP V0, addr - Jump to location nnn + V0. '''
    # The program counter is set to nnn plus the value of V0.
    for i in range(10):
      random.seed()
      V0 = random.randrange(0x100)
      addr = random.randrange(0x200, 0x10000)
      # Make sure the value is within the address range and it is an
      # even address.
      while((V0 + addr >= 4096) or (0 != (V0 + addr % 2))):
        addr = random.randrange(0x200, 0x10000)
        V0 = random.randrange(0x100)

      self.dut.V[0x0] = V0
      opcode = 0xB000 | addr
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.pc, V0 + addr)

  def test_rndvxbyte(self):
    ''' Test 0xCxkk - RND Vx, byte - Set Vx = random byte AND kk.'''
    # The interpreter generates a random number from 0 to 255, which is ANDed with the value of kk.
    # The results are stored in Vx.
    for x in range(len(self.dut.V)):
      random.seed()
      byte = random.randrange(0x100)
      opcode = 0xC000 | (x << 8) | byte
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      v = self.dut.V[(x + 1) % len(self.dut.V)]
      self.assertEqual(self.dut.V[x], v & byte)

  def test_skpvx(self):
    ''' Test 0xEx9E - Skip next instruction if key with the value of Vx is pressed. '''
    # Checks the keyboard, and if the key corresponding to the value of Vx is 
    # currently in the down position, PC is increased by 2.

    # Test for key being pressed.
    for key in range(256):
      self.dut.keyboard = [False] * len(self.dut.keyboard)
      self.dut.keyboard[key % len(self.dut.keyboard)] = True
      self.dut.V = [16] * len(self.dut.V)
      for x in range(len(self.dut.V)):
        self.dut.V[x] = key 
        opcode = 0xE09E | (x << 8)
        self.dut.write_opcode(opcode, 0x200)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, 0x204)
        self.dut.pc = 0x200

    self.dut.reset()

    # Test for key not being pressed.
    for key in range(256):
      self.dut.V = [16] * len(self.dut.V)
      for x in range(len(self.dut.V)):
        self.dut.V[x] = key 
        opcode = 0xE09E | (x << 8)
        self.dut.write_opcode(opcode, 0x200)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, 0x202)
        self.dut.pc = 0x200

  def test_sknpvx(self):
    ''' Test 0xExA1 - Skip next instruction if key with the value of Vx is not pressed. '''
    # Checks the keyboard, and if the key corresponding to the value of Vx is 
    # currently in the up position, PC is increased by 2.

    # Test for key being pressed.
    for key in range(256):
      self.dut.keyboard = [False] * len(self.dut.keyboard)
      self.dut.keyboard[key % len(self.dut.keyboard)] = True
      self.dut.V = [16] * len(self.dut.V)
      for x in range(len(self.dut.V)):
        self.dut.V[x] = key 
        opcode = 0xE0A1 | (x << 8)
        self.dut.write_opcode(opcode, 0x200)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, 0x202)
        self.dut.pc = 0x200

    self.dut.reset()

    # Test for key not being pressed.
    for key in range(256):
      self.dut.V = [16] * len(self.dut.V)
      for x in range(len(self.dut.V)):
        self.dut.V[x] = key 
        opcode = 0xE0A1 | (x << 8)
        self.dut.write_opcode(opcode, 0x200)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.pc, 0x204)
        self.dut.pc = 0x200

  def test_ldvxdt(self):
    ''' Test 0xFx07 - Set Vx = delay timer value. '''
    # The value of DT is placed into Vx
    for x in range(len(self.dut.V)):
      opcode = 0xF007 | (x << 8)
      for i in range(10):
        self.dut.delay_timer = random.randrange(256)
        self.dut.pc = 0x200
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.V[x], self.dut.delay_timer)

  def test_ldvxk(self):
    ''' Test 0xFx0A - Wait for a key press, store the value of the key in Vx
    '''
    # All execution stops until a key is pressed, then the value of that key is
    # stored in Vx.
    for x in range(len(self.dut.V)):
      for i in range(len(self.dut.keyboard)):
        # Unpress all the keys.
        self.dut.keyboard = [False] * len(self.dut.keyboard)

        random.seed()
        old_vx = self.dut.V[x]
        while(not self.dut.keyboard[i]):
          # 1 in 5 chances of pressing a key.
          self.dut.keyboard[i] = random.choice([False, False, True, False,
              False])
          opcode = 0xF00A | (x << 8)
          self.dut.write_opcode(opcode, self.dut.pc)
          self.dut.emulate_cycle()

          if self.dut.keyboard[i]:
            # If key was pressed then the key was copied into Vx.
            self.assertEqual(self.dut.V[x], i)
          else:
            # If key was not pressed then the key was not copied into Vx.
            self.assertEqual(self.dut.V[x], old_vx)

        self.dut.pc = 0x200

  def test_lddtvx(self):
    ''' Test 0xFx15 - Set delay timer = Vx. '''
    # DT is set equal to the value of Vx.
    for x in range(len(self.dut.V)):
      self.dut.V[x] = random.randrange(256)
      opcode = 0xF015 | (x << 8)
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.delay_timer, self.dut.V[x])

  def test_ldstvx(self):
    ''' Test 0xFx18 - Set sound timer = Vx. '''
    # ST is set equal to the value of Vx.
    for x in range(len(self.dut.V)):
      self.dut.V[x] = random.randrange(256)
      opcode = 0xF018 | (x << 8)
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.sound_timer, self.dut.V[x])

  def test_addivx(self):
    ''' Test 0xFx1E - Set I = I + Vx '''
    # The values of I and Vx are added, and the result is stored in I.
    for x in range(len(self.dut.V)):
      I = random.randrange(0x10000)
      Vx = random.randrange(256)
      self.dut.V[x] = Vx
      self.dut.I = I
      opcode = 0xF01E | (x << 8)
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      self.assertEqual(self.dut.I, I + Vx)

  def test_ldfvx(self):
    ''' Test 0xFx29 - LD F, Vx - Set I = location of sprite for digit Vx. In
    other words I will contain the address of the font character stored in Vx
    '''
    # The value of I is set to the location for the hexadecimal sprite
    # corresponding to the value of Vx.
    for x in range(len(self.dut.V)):
      opcode = 0xF029 | (x << 8)
      for char_nbr in range(16):
        self.dut.V[x] = char_nbr
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.I, char_nbr*5)

  def test_ldfvx(self):
    ''' Test 0xFx29 - LD F, Vx - Set I = location of sprite for digit Vx. In
    other words I will contain the address of the font character stored in Vx
    '''
    # The value of I is set to the location for the hexadecimal sprite
    # corresponding to the value of Vx.
    for x in range(len(self.dut.V)):
      opcode = 0xF029 | (x << 8)
      for char_nbr in range(16):
        self.dut.V[x] = char_nbr
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.I, char_nbr*5)

  def test_ldbvx(self):
    ''' Test 0xFx33 - LD B, Vx - Store BCD representation of Vx in memory
    locations I, I + 1, and I + 2.  '''
    # The interpreter takes the decimal value of Vx, and places the hundreds
    # digit in memory at location in I, the tens digit at location in I + 1,
    # and the ones digit a location I + 2.
    self.dut.I = 0x300
    for x in range(len(self.dut.V)):
      opcode = 0xF033 | (x << 8)
      for i in range(10):
        val = random.randrange(256)
        hundreds = val // 100
        tens = (val - hundreds * 100) // 10
        ones = val - hundreds*100 - tens*10
        self.dut.V[x] = val
        self.dut.write_opcode(opcode, self.dut.pc)
        self.dut.emulate_cycle()
        self.assertEqual(self.dut.read(self.dut.I), hundreds)
        self.assertEqual(self.dut.read(self.dut.I + 1), tens)
        self.assertEqual(self.dut.read(self.dut.I + 2), ones)
        self.dut.pc = 0x200

  def test_ldivx(self):
    ''' Test 0xFx55 - LD [I], Vx - Store registers V0 through Vx in memory
    starting at location I. '''
    # The interpreter copies the values of registers V0 through Vx into memory,
    # starting at the address in I.
    random.seed()
    for x in range(len(self.dut.V)):
      self.dut.V[x] = random.randrange(256)

    for i in range(10):
      self.dut.I = 0x300 + i*len(self.dut.V)
      x = random.randrange(len(self.dut.V))
      opcode = 0xF055 | (x << 8)
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      for j in range(x+1):
        self.assertEqual(self.dut.read(self.dut.I + j), self.dut.V[j])

  def test_ldvxi(self):
    ''' Test 0xFx65 - LD Vx, [I] - Read registers V0 through Vx from memory
    starting at location I. '''
    # The interpreter reads values from memory at location I into registers V0
    # through Vx.

    # Fill memory with random values.
    random.seed()
    for addr in range(0x300, 0x1000):
      self.dut.write(random.randrange(256), addr)

    for i in range(10):
      self.dut.I = random.randrange(0x300, 0x1000)
      x = random.randrange(len(self.dut.V))
      opcode = 0xF065 | (x << 8)
      self.dut.write_opcode(opcode, self.dut.pc)
      self.dut.emulate_cycle()
      for j in range(x+1):
        self.assertEqual(self.dut.read(self.dut.I + j), self.dut.V[j])


if '__main__' == __name__:
  unittest.main()
