import chip8
import pygame
import random

def main():
  chip = chip8.Cpu()
  chip.load_app('pong2.c8')

  # I - Initialize.
  pygame.init()

  # D - Display.
  display = pygame.display.set_mode((640, 320))

  # E - Entities.
  background = pygame.Surface(display.get_size())
  background.fill((0, 0, 0))
  background = background.convert()
  all_sprites = pygame.sprite.Group()
  for row in range(chip.rows):
    for col in range(chip.cols):
      all_sprites.add(Block(row, col, chip.gfx))

  # A - Action.
  clock = pygame.time.Clock()
  keep_going = True

  # A - Assign values.
  # L - Loop.
  while keep_going:

    # T - Timing.
    clock.tick(60) # 60 Frames per second.

    chip.emulate_cycle()

    # E - Events.
    for event in pygame.event.get():
      if pygame.QUIT == event.type:
        keep_going = False
      elif pygame.KEYDOWN == event.type:
        press_key(event.key, chip.keyboard, True)
      elif pygame.KEYUP == event.type:
        press_key(event.key, chip.keyboard, False)

    # R - Refresh display.
    if chip.draw_flag:
      all_sprites.clear(display, background)
      all_sprites.update()
      all_sprites.draw(display)
      pygame.display.flip()


if '__main__' == __name__:
  main()
