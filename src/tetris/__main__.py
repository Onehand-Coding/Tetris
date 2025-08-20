#!/usr/bin/env python
import pygame
from pygame import Rect, Surface
import random
import os
import kezmenu

from .tetrominoes import list_of_tetrominoes
from .tetrominoes import rotate

from .scores import load_score, write_score

class GameOver(Exception):
    """Exception used for its control flow properties"""

# Global sound manager
sound_manager = None


def get_sound(filename):
    try:
        sound = pygame.mixer.Sound(os.path.join(os.path.dirname(__file__), "resources", "sounds", filename))
        # Wrap the sound with a play method that uses the sound manager
        class ManagedSound:
            def __init__(self, sound):
                self._sound = sound
                
            def play(self):
                global sound_manager
                if sound_manager:
                    sound_manager.play_sound(self._sound)
                else:
                    # Fallback if sound manager not initialized
                    try:
                        self._sound.play()
                    except:
                        pass
                        
        return ManagedSound(sound)
    except (pygame.error, FileNotFoundError):
        # Return a dummy sound object that doesn't crash when play() is called
        class DummySound:
            def play(self):
                pass
        return DummySound()

BGCOLOR = (15, 15, 20)
BORDERCOLOR = (140, 140, 140)

BLOCKSIZE = 30
BORDERWIDTH = 10

MATRIS_OFFSET = 20

MATRIX_WIDTH = 10
MATRIX_HEIGHT = 22

LEFT_MARGIN = 340

WIDTH = MATRIX_WIDTH*BLOCKSIZE + BORDERWIDTH*2 + MATRIS_OFFSET*2 + LEFT_MARGIN
HEIGHT = (MATRIX_HEIGHT-2)*BLOCKSIZE + BORDERWIDTH*2 + MATRIS_OFFSET*2

TRICKY_CENTERX = WIDTH-(WIDTH-(MATRIS_OFFSET+BLOCKSIZE*MATRIX_WIDTH+BORDERWIDTH*2))/2

VISIBLE_MATRIX_HEIGHT = MATRIX_HEIGHT - 2


class Matris(object):
    def __init__(self, screen):
        self.surface = screen.subsurface(Rect((MATRIS_OFFSET+BORDERWIDTH, MATRIS_OFFSET+BORDERWIDTH),
                                              (MATRIX_WIDTH * BLOCKSIZE, (MATRIX_HEIGHT-2) * BLOCKSIZE)))

        self.matrix = dict()
        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                self.matrix[(y,x)] = None
        """
        `self.matrix` is the current state of the tetris board, that is, it records which squares are
        currently occupied. It does not include the falling tetromino. The information relating to the
        falling tetromino is managed by `self.set_tetrominoes` instead. When the falling tetromino "dies",
        it will be placed in `self.matrix`.
        """

        self.next_tetromino = random.choice(list_of_tetrominoes)
        self.set_tetrominoes()
        self.tetromino_rotation = 0
        self.downwards_timer = 0
        self.base_downwards_speed = 0.4 # Move down every 400 ms

        self.movement_keys = {'left': 0, 'right': 0}
        self.movement_keys_speed = 0.05
        self.movement_keys_timer = (-self.movement_keys_speed)*2

        self.level = 1
        self.score = 0
        self.lines = 0

        self.combo = 1 # Combo will increase when you clear lines with several tetrominos in a row
        
        self.paused = False

        self.highscore = load_score()
        self.played_highscorebeaten_sound = False

        # Track if a hard drop occurred for sound effects
        self.hard_drop_occurred = False

        self.levelup_sound  = get_sound("levelup.wav")
        self.gameover_sound = get_sound("gameover.wav")
        self.linescleared_sound = get_sound("linecleared.wav")
        self.highscorebeaten_sound = get_sound("highscorebeaten.wav")
        self.clear_sound = get_sound("clear.wav")
        self.drop_sound = get_sound("drop.wav")
        self.lateralmove_sound = get_sound("lateralmove.wav")
        self.rotate_sound = get_sound("rotate.wav")
        self.select_sound = get_sound("select.wav")
        self.start_sound = get_sound("start.wav")
        self.tetris_sound = get_sound("tetris.wav")


    def set_tetrominoes(self):
        self.current_tetromino = self.next_tetromino
        self.next_tetromino = random.choice(list_of_tetrominoes)
        self.surface_of_next_tetromino = self.construct_surface_of_next_tetromino()
        self.tetromino_position = (0,4) if len(self.current_tetromino.shape) == 2 else (0, 3)
        self.tetromino_rotation = 0
        self.tetromino_block = self.block(self.current_tetromino.color)
        self.shadow_block = self.block(self.current_tetromino.color, shadow=True)

    
    def hard_drop(self):
        amount = 0
        while self.request_movement('down'):
            amount += 1
        self.score += 10*amount
        self.drop_sound.play()
        self.hard_drop_occurred = True

        self.lock_tetromino()


    def update(self, timepassed):
        self.needs_redraw = False
        
        pressed = lambda key: event.type == pygame.KEYDOWN and event.key == key
        unpressed = lambda key: event.type == pygame.KEYUP and event.key == key

        events = pygame.event.get()
        
        for event in events:
            if pressed(pygame.K_p):
                self.surface.fill((0,0,0))
                self.needs_redraw = True
                self.paused = not self.paused
            elif event.type == pygame.QUIT:
                self.gameover(full_exit=True)
            elif pressed(pygame.K_ESCAPE):
                self.gameover()

        if self.paused:
            return self.needs_redraw

        for event in events:
            if pressed(pygame.K_SPACE):
                self.hard_drop()
            elif pressed(pygame.K_UP) or pressed(pygame.K_w):
                self.request_rotation()

            elif pressed(pygame.K_LEFT) or pressed(pygame.K_a):
                self.request_movement('left')
                self.movement_keys['left'] = 1
            elif pressed(pygame.K_RIGHT) or pressed(pygame.K_d):
                self.request_movement('right')
                self.movement_keys['right'] = 1

            elif unpressed(pygame.K_LEFT) or unpressed(pygame.K_a):
                self.movement_keys['left'] = 0
                self.movement_keys_timer = (-self.movement_keys_speed)*2
            elif unpressed(pygame.K_RIGHT) or unpressed(pygame.K_d):
                self.movement_keys['right'] = 0
                self.movement_keys_timer = (-self.movement_keys_speed)*2




        self.downwards_speed = self.base_downwards_speed ** (1 + self.level/10.)

        self.downwards_timer += timepassed
        downwards_speed = self.downwards_speed*0.10 if any([pygame.key.get_pressed()[pygame.K_DOWN],
                                                            pygame.key.get_pressed()[pygame.K_s]]) else self.downwards_speed
        if self.downwards_timer > downwards_speed:
            if not self.request_movement('down'):
                self.lock_tetromino()

            self.downwards_timer %= downwards_speed


        if any(self.movement_keys.values()):
            self.movement_keys_timer += timepassed
        if self.movement_keys_timer > self.movement_keys_speed:
            self.request_movement('right' if self.movement_keys['right'] else 'left')
            self.movement_keys_timer %= self.movement_keys_speed
        
        return self.needs_redraw

    def draw_surface(self):
        with_tetromino = self.blend(matrix=self.place_shadow())

        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):

                #                                       I hide the 2 first rows by drawing them outside of the surface
                block_location = Rect(x*BLOCKSIZE, (y*BLOCKSIZE - 2*BLOCKSIZE), BLOCKSIZE, BLOCKSIZE)
                if with_tetromino[(y,x)] is None:
                    self.surface.fill(BGCOLOR, block_location)
                else:
                    if with_tetromino[(y,x)][0] == 'shadow':
                        self.surface.fill(BGCOLOR, block_location)
                    
                    self.surface.blit(with_tetromino[(y,x)][1], block_location)
                    
    def gameover(self, full_exit=False):
        """
        Gameover occurs when a new tetromino does not fit after the old one has died, either
        after a "natural" drop or a hard drop by the player. That is why `self.lock_tetromino`
        is responsible for checking if it's game over.
        """

        write_score(self.score)
        
        if full_exit:
            exit()
        else:
            raise GameOver("Sucker!")

    def place_shadow(self):
        posY, posX = self.tetromino_position
        while self.blend(position=(posY, posX)):
            posY += 1

        position = (posY-1, posX)

        return self.blend(position=position, shadow=True)

    def fits_in_matrix(self, shape, position):
        posY, posX = position
        for x in range(posX, posX+len(shape)):
            for y in range(posY, posY+len(shape)):
                if self.matrix.get((y, x), False) is False and shape[y-posY][x-posX]: # outside matrix
                    return False

        return position
                    

    def request_rotation(self):
        rotation = (self.tetromino_rotation + 1) % 4
        shape = self.rotated(rotation)

        y, x = self.tetromino_position

        position = (self.fits_in_matrix(shape, (y, x)) or
                    self.fits_in_matrix(shape, (y, x+1)) or
                    self.fits_in_matrix(shape, (y, x-1)) or
                    self.fits_in_matrix(shape, (y, x+2)) or
                    self.fits_in_matrix(shape, (y, x-2)))
        # ^ That's how wall-kick is implemented

        if position and self.blend(shape, position):
            self.tetromino_rotation = rotation
            self.tetromino_position = position
            self.rotate_sound.play()
            self.needs_redraw = True
            return self.tetromino_rotation
        else:
            return False
            
    def request_movement(self, direction):
        posY, posX = self.tetromino_position
        if direction == 'left' and self.blend(position=(posY, posX-1)):
            self.tetromino_position = (posY, posX-1)
            self.lateralmove_sound.play()
            self.needs_redraw = True
            return self.tetromino_position
        elif direction == 'right' and self.blend(position=(posY, posX+1)):
            self.tetromino_position = (posY, posX+1)
            self.lateralmove_sound.play()
            self.needs_redraw = True
            return self.tetromino_position
        elif direction == 'up' and self.blend(position=(posY-1, posX)):
            self.needs_redraw = True
            self.tetromino_position = (posY-1, posX)
            return self.tetromino_position
        elif direction == 'down' and self.blend(position=(posY+1, posX)):
            self.needs_redraw = True
            self.tetromino_position = (posY+1, posX)
            return self.tetromino_position
        else:
            return False

    def rotated(self, rotation=None):
        if rotation is None:
            rotation = self.tetromino_rotation
        return rotate(self.current_tetromino.shape, rotation)

    def block(self, color, shadow=False):
        colors = {'blue':   (105, 105, 255),
                  'yellow': (225, 242, 41),
                  'pink':   (242, 41, 195),
                  'green':  (22, 181, 64),
                  'red':    (204, 22, 22),
                  'orange': (245, 144, 12),
                  'cyan':   (10, 255, 226)}


        if shadow:
            end = [90] # end is the alpha value
        else:
            end = [] # Adding this to the end will not change the array, thus no alpha value

        border = Surface((BLOCKSIZE, BLOCKSIZE), pygame.SRCALPHA, 32)
        border.fill(list(map(lambda c: c*0.5, colors[color])) + end)

        borderwidth = 2

        box = Surface((BLOCKSIZE-borderwidth*2, BLOCKSIZE-borderwidth*2), pygame.SRCALPHA, 32)
        boxarr = pygame.PixelArray(box)
        for x in range(len(boxarr)):
            for y in range(len(boxarr)):
                boxarr[x][y] = tuple(list(map(lambda c: min(255, int(c*random.uniform(0.8, 1.2))), colors[color])) + end) 

        del boxarr # deleting boxarr or else the box surface will be 'locked' or something like that and won't blit.
        border.blit(box, Rect(borderwidth, borderwidth, 0, 0))


        return border

    def lock_tetromino(self):
        """
        This method is called whenever the falling tetromino "dies". `self.matrix` is updated,
        the lines are counted and cleared, and a new tetromino is chosen.
        """
        self.matrix = self.blend()

        lines_cleared = self.remove_lines()
        self.lines += lines_cleared

        if lines_cleared:
            # Play appropriate line clear sound
            if lines_cleared == 1:
                self.clear_sound.play()
            elif lines_cleared == 2:
                self.clear_sound.play()
            elif lines_cleared == 3:
                self.clear_sound.play()
            elif lines_cleared >= 4:
                self.tetris_sound.play()
            else:
                self.linescleared_sound.play()
                
            self.score += 100 * (lines_cleared**2) * self.combo

            if not self.played_highscorebeaten_sound and self.score > self.highscore:
                if self.highscore != 0:
                    self.highscorebeaten_sound.play()
                self.played_highscorebeaten_sound = True

        if self.lines >= self.level*10:
            self.levelup_sound.play()
            self.level += 1

        self.combo = self.combo + 1 if lines_cleared else 1

        # Play drop sound when tetromino locks naturally (not hard dropped)
        if not self.hard_drop_occurred and not lines_cleared:
            self.drop_sound.play()

        self.set_tetrominoes()
        
        # Reset the hard drop flag for the next piece
        self.hard_drop_occurred = False

        if not self.blend():
            self.gameover_sound.play()
            self.gameover()
            
        self.needs_redraw = True

    def remove_lines(self):
        lines = []
        for y in range(MATRIX_HEIGHT):
            line = (y, [])
            for x in range(MATRIX_WIDTH):
                if self.matrix[(y,x)]:
                    line[1].append(x)
            if len(line[1]) == MATRIX_WIDTH:
                lines.append(y)

        for line in sorted(lines):
            for x in range(MATRIX_WIDTH):
                self.matrix[(line,x)] = None
            for y in range(0, line+1)[::-1]:
                for x in range(MATRIX_WIDTH):
                    self.matrix[(y,x)] = self.matrix.get((y-1,x), None)

        return len(lines)

    def blend(self, shape=None, position=None, matrix=None, shadow=False):
        """
        Does `shape` at `position` fit in `matrix`? If so, return a new copy of `matrix` where all
        the squares of `shape` have been placed in `matrix`. Otherwise, return False.
        
        This method is often used simply as a test, for example to see if an action by the player is valid.
        It is also used in `self.draw_surface` to paint the falling tetromino and its shadow on the screen.
        """
        if shape is None:
            shape = self.rotated()
        if position is None:
            position = self.tetromino_position

        copy = dict(self.matrix if matrix is None else matrix)
        posY, posX = position
        for x in range(posX, posX+len(shape)):
            for y in range(posY, posY+len(shape)):
                if (copy.get((y, x), False) is False and shape[y-posY][x-posX] # shape is outside the matrix
                    or # coordinate is occupied by something else which isn't a shadow
                    copy.get((y,x)) and shape[y-posY][x-posX] and copy[(y,x)][0] != 'shadow'):

                    return False # Blend failed; `shape` at `position` breaks the matrix

                elif shape[y-posY][x-posX]:
                    copy[(y,x)] = ('shadow', self.shadow_block) if shadow else ('block', self.tetromino_block)

        return copy

    def construct_surface_of_next_tetromino(self):
        shape = self.next_tetromino.shape
        surf = Surface((len(shape)*BLOCKSIZE, len(shape)*BLOCKSIZE), pygame.SRCALPHA, 32)

        for y in range(len(shape)):
            for x in range(len(shape)):
                if shape[y][x]:
                    surf.blit(self.block(self.next_tetromino.color), (x*BLOCKSIZE, y*BLOCKSIZE))
        return surf

class Game(object):
    def main(self, screen):
        clock = pygame.time.Clock()
        self.screen = screen

        self.matris = Matris(screen)
        
        screen.blit(construct_nightmare(screen.get_size()), (0,0))
        
        matris_border = Surface((MATRIX_WIDTH*BLOCKSIZE+BORDERWIDTH*2, VISIBLE_MATRIX_HEIGHT*BLOCKSIZE+BORDERWIDTH*2))
        matris_border.fill(BORDERCOLOR)
        screen.blit(matris_border, (MATRIS_OFFSET,MATRIS_OFFSET))
        
        self.redraw()

        while True:
            try:
                timepassed = clock.tick(50)
                if self.matris.update((timepassed / 1000.) if not self.matris.paused else 0):
                    self.redraw()
            except GameOver:
                return
      

    def redraw(self):
        if not self.matris.paused:
            self.blit_next_tetromino(self.matris.surface_of_next_tetromino)
            self.blit_info()

            self.matris.draw_surface()

        pygame.display.flip()


    def blit_info(self):
        textcolor = (255, 255, 255)
        font = pygame.font.Font(None, 30)
        width = (WIDTH-(MATRIS_OFFSET+BLOCKSIZE*MATRIX_WIDTH+BORDERWIDTH*2)) - MATRIS_OFFSET*2

        def renderpair(text, val):
            text = font.render(text, True, textcolor)
            val = font.render(str(val), True, textcolor)

            surf = Surface((width, text.get_rect().height + BORDERWIDTH*2), pygame.SRCALPHA, 32)

            surf.blit(text, text.get_rect(top=BORDERWIDTH+10, left=BORDERWIDTH+10))
            surf.blit(val, val.get_rect(top=BORDERWIDTH+10, right=width-(BORDERWIDTH+10)))
            return surf

        scoresurf = renderpair("Score", self.matris.score)
        levelsurf = renderpair("Level", self.matris.level)
        linessurf = renderpair("Lines", self.matris.lines)
        combosurf = renderpair("Combo", "x{}".format(self.matris.combo))

        height = 20 + (levelsurf.get_rect().height + 
                       scoresurf.get_rect().height +
                       linessurf.get_rect().height + 
                       combosurf.get_rect().height )

        area = Surface((width, height))
        area.fill(BORDERCOLOR)
        area.fill(BGCOLOR, Rect(BORDERWIDTH, BORDERWIDTH, width-BORDERWIDTH*2, height-BORDERWIDTH*2))

        area.blit(levelsurf, (0,0))
        area.blit(scoresurf, (0, levelsurf.get_rect().height))
        area.blit(linessurf, (0, levelsurf.get_rect().height + scoresurf.get_rect().height))
        area.blit(combosurf, (0, levelsurf.get_rect().height + scoresurf.get_rect().height + linessurf.get_rect().height))

        self.screen.blit(area, area.get_rect(bottom=HEIGHT-MATRIS_OFFSET, centerx=TRICKY_CENTERX))


    def blit_next_tetromino(self, tetromino_surf):
        area = Surface((BLOCKSIZE*5, BLOCKSIZE*5))
        area.fill(BORDERCOLOR)
        area.fill(BGCOLOR, Rect(BORDERWIDTH, BORDERWIDTH, BLOCKSIZE*5-BORDERWIDTH*2, BLOCKSIZE*5-BORDERWIDTH*2))

        areasize = area.get_size()[0]
        tetromino_surf_size = tetromino_surf.get_size()[0]
        # ^^ I'm assuming width and height are the same

        center = areasize/2 - tetromino_surf_size/2
        area.blit(tetromino_surf, (center, center))

        self.screen.blit(area, area.get_rect(top=MATRIS_OFFSET, centerx=TRICKY_CENTERX))

class Menu(object):
    running = True
    def main(self, screen):
        clock = pygame.time.Clock()
        
        # Create main menu
        menu = kezmenu.KezMenu(
            ['Play!', lambda: self.start_game(screen)],
            ['Options', lambda: self.show_options(screen)],
            ['High Scores', lambda: self.show_high_scores(screen)],
            ['Quit', lambda: setattr(self, 'running', False)],
        )
        menu.position = (50, 50)
        # Set a larger base font size
        menu.font = pygame.font.Font(None, 60)
        menu.color = (255,255,255)
        menu.focus_color = (40, 200, 40)

        nightmare = construct_nightmare(screen.get_size())
        highscoresurf = self.construct_highscoresurf()

        timepassed = clock.tick(30) / 1000.

        while self.running:
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    exit()

            menu.update(events, timepassed)

            timepassed = clock.tick(30) / 1000.

            if timepassed > 1: # A game has most likely been played 
                highscoresurf = self.construct_highscoresurf()

            screen.blit(nightmare, (0,0))
            screen.blit(highscoresurf, highscoresurf.get_rect(right=WIDTH-50, bottom=HEIGHT-50))
            menu.draw(screen)
            pygame.display.flip()

    def start_game(self, screen):
        """Start the game and play the start sound"""
        # Play start sound
        try:
            start_sound = get_sound("start.wav")
            start_sound.play()
        except:
            pass  # If sound fails, continue anyway
        Game().main(screen)

    def show_options(self, screen):
        """Show the options menu with custom UI elements"""
        global sound_manager
        
        # Play select sound
        try:
            select_sound = get_sound("select.wav")
            sound_manager.play_sound(select_sound)
        except:
            pass  # If sound fails, continue anyway
            
        clock = pygame.time.Clock()
        nightmare = construct_nightmare(screen.get_size())
        
        # Font setup
        title_font = pygame.font.Font(None, 70)
        option_font = pygame.font.Font(None, 50)
        
        # UI element positions
        title_y = 100
        mute_y = 200
        volume_y = 300
        back_y = 400
        
        # Slider properties
        slider_x = WIDTH // 2 - 100
        slider_width = 200
        slider_height = 20
        slider_knob_radius = 10
        
        # Checkbox properties
        checkbox_size = 30
        checkbox_x = WIDTH // 2 - 100
        checkbox_y = mute_y - checkbox_size // 2
        
        # Button properties
        button_width = 200
        button_height = 50
        
        # Mouse state
        mouse_pressed = False
        
        while True:
            events = pygame.event.get()
            
            # Handle events
            for event in events:
                if event.type == pygame.QUIT:
                    exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return  # Return to main menu
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        mouse_pressed = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left mouse button
                        mouse_pressed = False
            
            # Get mouse position
            mouse_x, mouse_y = pygame.mouse.get_pos()
            
            # Handle mute/unmute checkbox
            checkbox_rect = pygame.Rect(checkbox_x, checkbox_y, checkbox_size, checkbox_size)
            if mouse_pressed and checkbox_rect.collidepoint(mouse_x, mouse_y):
                sound_manager.toggle_sound()
                # Play sound effect for checkbox toggle
                try:
                    select_sound = get_sound("select.wav")
                    sound_manager.play_sound(select_sound)
                except:
                    pass
                mouse_pressed = False  # Prevent continuous toggling
            
            # Handle volume slider
            slider_rect = pygame.Rect(slider_x, volume_y - slider_height // 2, slider_width, slider_height)
            if mouse_pressed and slider_rect.collidepoint(mouse_x, mouse_y):
                # Calculate new volume based on mouse position
                relative_x = max(0, min(slider_width, mouse_x - slider_x))
                new_volume = relative_x / slider_width
                sound_manager.sound_volume = new_volume
                if not sound_manager.sound_muted:
                    pygame.mixer.music.set_volume(new_volume)
            
            # Handle back button
            back_button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, back_y - button_height // 2, button_width, button_height)
            if (mouse_pressed and back_button_rect.collidepoint(mouse_x, mouse_y)) or \
               any(event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE) for event in events):
                # Play sound effect for back button
                try:
                    select_sound = get_sound("select.wav")
                    sound_manager.play_sound(select_sound)
                except:
                    pass
                return  # Return to main menu
            
            # Draw background
            screen.blit(nightmare, (0, 0))
            
            # Draw title
            title = title_font.render("OPTIONS", True, (255, 255, 255))
            screen.blit(title, title.get_rect(centerx=WIDTH // 2, top=title_y))
            
            # Draw mute/unmute checkbox
            pygame.draw.rect(screen, (255, 255, 255), checkbox_rect, 2)
            if sound_manager.sound_muted:
                # Draw checkmark
                pygame.draw.line(screen, (255, 255, 255), 
                                (checkbox_x + 5, checkbox_y + 15),
                                (checkbox_x + 12, checkbox_y + 22), 3)
                pygame.draw.line(screen, (255, 255, 255),
                                (checkbox_x + 12, checkbox_y + 22),
                                (checkbox_x + 25, checkbox_y + 8), 3)
            
            # Draw mute label
            mute_text = option_font.render("Mute Sound", True, (255, 255, 255))
            screen.blit(mute_text, (checkbox_x + checkbox_size + 10, mute_y - mute_text.get_height() // 2))
            
            # Draw volume label
            volume_label = option_font.render("Volume", True, (255, 255, 255))
            screen.blit(volume_label, volume_label.get_rect(centerx=WIDTH // 2, centery=volume_y - 40))
            
            # Draw volume slider
            pygame.draw.rect(screen, (100, 100, 100), slider_rect)
            pygame.draw.rect(screen, (255, 255, 255), slider_rect, 2)
            
            # Draw slider fill
            fill_width = int(slider_width * sound_manager.sound_volume)
            if fill_width > 0:
                fill_rect = pygame.Rect(slider_x, volume_y - slider_height // 2, fill_width, slider_height)
                pygame.draw.rect(screen, (40, 200, 40), fill_rect)
            
            # Draw slider knob
            knob_x = slider_x + int(slider_width * sound_manager.sound_volume)
            knob_y = volume_y
            pygame.draw.circle(screen, (255, 255, 255), (knob_x, knob_y), slider_knob_radius)
            pygame.draw.circle(screen, (40, 200, 40), (knob_x, knob_y), slider_knob_radius - 2)
            
            # Draw volume percentage
            volume_text = option_font.render(f"{int(sound_manager.sound_volume * 100)}%", True, (255, 255, 255))
            screen.blit(volume_text, volume_text.get_rect(centerx=WIDTH // 2, centery=volume_y + 40))
            
            # Draw back button
            back_color = (40, 200, 40) if back_button_rect.collidepoint(mouse_x, mouse_y) else (100, 100, 100)
            pygame.draw.rect(screen, back_color, back_button_rect, border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255), back_button_rect, 2, border_radius=10)
            back_text = option_font.render("BACK", True, (255, 255, 255))
            screen.blit(back_text, back_text.get_rect(center=back_button_rect.center))
            
            pygame.display.flip()
            clock.tick(30)

    def toggle_sound(self):
        """Toggle sound mute/unmute"""
        self.sound_muted = not self.sound_muted
        if self.sound_muted:
            pygame.mixer.music.set_volume(0.0)
        else:
            pygame.mixer.music.set_volume(self.sound_volume)
            
        # Play confirmation sound if unmuting
        if not self.sound_muted:
            try:
                select_sound = get_sound("select.wav")
                select_sound.play()
            except:
                pass

    def adjust_volume(self, delta):
        """Adjust sound volume"""
        self.sound_volume = max(0.0, min(1.0, self.sound_volume + delta))
        if not self.sound_muted:
            pygame.mixer.music.set_volume(self.sound_volume)
        
        # Play confirmation sound
        try:
            select_sound = get_sound("select.wav")
            if not self.sound_muted:
                select_sound.play()
        except:
            pass

    def construct_highscoresurf(self):
        font = pygame.font.Font(None, 50)
        highscore = load_score()
        text = "Highscore: {}".format(highscore)
        return font.render(text, True, (255,255,255))

    def show_high_scores(self, screen):
        """Show the high scores screen"""
        global sound_manager
        
        # Play select sound
        try:
            select_sound = get_sound("select.wav")
            sound_manager.play_sound(select_sound)
        except:
            pass  # If sound fails, continue anyway
            
        clock = pygame.time.Clock()
        
        # Load high scores
        from .scores import load_high_scores
        highscores = load_high_scores(5)  # Load top 5 scores
        
        # Fonts
        font_large = pygame.font.Font(None, 70)
        font_medium = pygame.font.Font(None, 50)
        font_small = pygame.font.Font(None, 40)
        
        # Title
        title = font_large.render("HIGH SCORES", True, (255, 255, 255))
        
        # Back button
        button_width = 200
        button_height = 50
        back_button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, HEIGHT - 100, button_width, button_height)
        
        nightmare = construct_nightmare(screen.get_size())
        
        while True:
            events = pygame.event.get()
            
            # Handle events
            for event in events:
                if event.type == pygame.QUIT:
                    exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Play sound effect for back button
                        try:
                            select_sound = get_sound("select.wav")
                            sound_manager.play_sound(select_sound)
                        except:
                            pass
                        return  # Return to main menu
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        if back_button_rect.collidepoint(event.pos):
                            # Play sound effect for back button
                            try:
                                select_sound = get_sound("select.wav")
                                sound_manager.play_sound(select_sound)
                            except:
                                pass
                            return  # Return to main menu
            
            # Draw background
            screen.blit(nightmare, (0, 0))
            
            # Draw title
            screen.blit(title, title.get_rect(centerx=WIDTH/2, top=50))
            
            # Draw high scores
            if highscores:
                for i, score in enumerate(highscores):
                    score_text = font_medium.render(f"{i+1}. {score}", True, (255, 255, 255))
                    screen.blit(score_text, score_text.get_rect(centerx=WIDTH/2, top=150 + i*60))
            else:
                no_scores_text = font_medium.render("No scores yet!", True, (255, 255, 255))
                screen.blit(no_scores_text, no_scores_text.get_rect(centerx=WIDTH/2, top=150))
            
            # Draw instruction
            instruction = font_small.render("Press ESC or click BACK to return", True, (200, 200, 200))
            screen.blit(instruction, instruction.get_rect(centerx=WIDTH/2, top=HEIGHT - 150))
            
            # Draw back button
            mouse_x, mouse_y = pygame.mouse.get_pos()
            back_color = (40, 200, 40) if back_button_rect.collidepoint(mouse_x, mouse_y) else (100, 100, 100)
            pygame.draw.rect(screen, back_color, back_button_rect, border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255), back_button_rect, 2, border_radius=10)
            back_text = font_small.render("BACK", True, (255, 255, 255))
            screen.blit(back_text, back_text.get_rect(center=back_button_rect.center))
            
            pygame.display.flip()
            clock.tick(30)

    def play_sound(self, sound):
        """Play a sound if sound is not muted"""
        # This would need to be connected to the menu's sound settings
        # For now, we'll just play the sound directly
        # In a full implementation, we'd check the global sound settings
        try:
            sound.play()
        except:
            pass


def construct_nightmare(size):
    surf = Surface(size)

    boxsize = 8
    bordersize = 1
    vals = '1235' # only the lower values, for darker colors and greater fear
    arr = pygame.PixelArray(surf)
    for x in range(0, len(arr), boxsize):
        for y in range(0, len(arr[x]), boxsize):

            color = int(''.join([random.choice(vals) + random.choice(vals) for _ in range(3)]), 16)

            for LX in range(x, x+(boxsize - bordersize)):
                for LY in range(y, y+(boxsize - bordersize)):
                    if LX < len(arr) and LY < len(arr[x]):
                        arr[LX][LY] = color
    del arr
    return surf


class SoundManager:
    """Manages sound settings for the entire game"""
    def __init__(self):
        self.sound_muted = False
        self.sound_volume = 0.5  # Volume level (0.0 to 1.0)
        
    def toggle_sound(self):
        """Toggle sound mute/unmute"""
        self.sound_muted = not self.sound_muted
        if self.sound_muted:
            pygame.mixer.music.set_volume(0.0)
        else:
            pygame.mixer.music.set_volume(self.sound_volume)
            
    def adjust_volume(self, delta):
        """Adjust sound volume"""
        self.sound_volume = max(0.0, min(1.0, self.sound_volume + delta))
        if not self.sound_muted:
            pygame.mixer.music.set_volume(self.sound_volume)
            
    def play_sound(self, sound):
        """Play a sound if sound is not muted"""
        if not self.sound_muted:
            try:
                sound.play()
            except:
                pass


def main():
    global sound_manager
    
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()

    # Initialize mixer for sound
    pygame.mixer.init()
    
    # Initialize sound manager
    sound_manager = SoundManager()
    
    # Load and play background music
    try:
        background_music = os.path.join(os.path.dirname(__file__), "resources", "sounds", "background.wav")
        pygame.mixer.music.load(background_music)
        pygame.mixer.music.play(-1)  # Loop indefinitely
        pygame.mixer.music.set_volume(sound_manager.sound_volume)  # Set initial volume
    except (pygame.error, FileNotFoundError):
        # If background music is not found, continue without it
        pass

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MaTris")
    Menu().main(screen)

if __name__ == '__main__':
    main()
