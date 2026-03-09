import arcade
import sqlite3
import os
from PIL import Image

PLAYER_ANIM_SPEED = 0.08

ASSET_FLY_1 = "project3/flyFly1.png"
ASSET_FLY_2 = "project3/flyFly2.png"
FLY_SPEED = 2.5
FLY_ANIMATION_SPEED = 0.15

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Platformer: Snail Enemy Final"

TILE_SCALING = 1.0
GRAVITY = 1.0
MOVEMENT_SPEED = 4
ICE_SPEED_FACTOR = 1.3
JUMP_STRENGTH = 18
CAMERA_SPEED = 0.1

SNAIL_SPEED = 2
SNAIL_ANIMATION_SPEED = 0.2

PLATFORM_SPEED = 2
PLATFORM_LEFT_LIMIT = 500
PLATFORM_RIGHT_LIMIT = 1200

ASSET_PLAYER = "project3/p3_stand.png"
ASSET_SNAIL_1 = "project3/snailWalk1.png"
ASSET_SNAIL_2 = "project3/snailWalk2.png"
ASSET_COIN = "project3/coinGold.png"
ASSET_PLATFORM = "project3/lollipopRed.png"
ASSET_MAP = "project3/game33.tmx"
ASSET_MUSIC = "project3/cutemusic.mp3"


WALKING_SOUND = "project3/walking-fast-on-gravel.mp3"
COIN_SOUND = "project3/Voicy_Jutsu - Naruto.mp3"


class DatabaseController:
    def __init__(self, database_path="game_stats.db"):
        self.database_path = database_path
        self.create_table()

    def create_table(self):
        connection = sqlite3.connect(self.database_path)
        cursor = connection.cursor()
        query = """
        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coins_count INTEGER,
            jumps_count INTEGER,
            deaths_count INTEGER
        )
        """
        cursor.execute(query)
        connection.commit()
        connection.close()

    def insert_session_stats(self, coins, jumps, deaths):
        connection = sqlite3.connect(self.database_path)
        cursor = connection.cursor()
        query = "INSERT INTO game_stats (coins_count, jumps_count, deaths_count) VALUES (?, ?, ?)"
        cursor.execute(query, (coins, jumps, deaths))
        connection.commit()
        connection.close()


def get_texture_pair(path):
    main_texture = arcade.load_texture(path)
    image_file = Image.open(path)
    reversed_image = image_file.transpose(Image.FLIP_LEFT_RIGHT)
    reversed_texture = arcade.Texture(reversed_image)
    return [reversed_texture, main_texture]


class MovingPlatform(arcade.Sprite):
    def __init__(self, path, scale, x, y, l_limit, r_limit, speed):
        super().__init__(path, scale)
        self.center_x = x
        self.center_y = y
        self.change_x = speed
        self.boundary_left = l_limit
        self.boundary_right = r_limit

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        if self.right > self.boundary_right:
            self.change_x = -abs(self.change_x)
        elif self.left < self.boundary_left:
            self.change_x = abs(self.change_x)


class SnailEnemy(arcade.Sprite):
    def __init__(self, x, y, left_lim, right_lim):
        super().__init__()
        self.anim_textures = []
        self.anim_textures.append(get_texture_pair(ASSET_SNAIL_1))
        self.anim_textures.append(get_texture_pair(ASSET_SNAIL_2))
        self.texture = self.anim_textures[0][0]
        self.center_x = x
        self.center_y = y
        self.change_x = SNAIL_SPEED
        self.left_limit = left_lim
        self.right_limit = right_lim
        self.frame_index = 0
        self.anim_timer = 0

    def process_animation(self, delta_time):
        self.anim_timer += delta_time
        if self.anim_timer > SNAIL_ANIMATION_SPEED:
            self.anim_timer = 0
            self.frame_index = 1 - self.frame_index
            look_direction = 0 if self.change_x > 0 else 1
            self.texture = self.anim_textures[self.frame_index][look_direction]

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        if self.left < self.left_limit:
            self.change_x = SNAIL_SPEED
        elif self.right > self.right_limit:
            self.change_x = -SNAIL_SPEED
        self.process_animation(delta_time)


class HUD:
    def __init__(self):
        self.score_text = arcade.Text("", 20, 20, arcade.color.BLACK, 14, bold=True)

    def update_text(self, coins, deaths):
        self.score_text.text = f"Монеты: {coins} | Смерти: {deaths}"

    def draw(self):
        self.score_text.draw()


class FlyingEnemy(arcade.Sprite):
    def __init__(self, x, y, player_sprite):
        super().__init__()
        self.player = player_sprite

        self.anim_textures = []
        self.anim_textures.append(get_texture_pair(ASSET_FLY_1))
        self.anim_textures.append(get_texture_pair(ASSET_FLY_2))

        self.texture = self.anim_textures[0][0]
        self.center_x = x
        self.center_y = y
        self.frame_index = 0
        self.anim_timer = 0

    def update(self, delta_time: float = 1 / 60):
        dx = self.player.center_x - self.center_x
        dy = self.player.center_y - self.center_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance > 0:
            self.change_x = (dx / distance) * FLY_SPEED
            self.change_y = (dy / distance) * FLY_SPEED

        self.center_x += self.change_x
        self.center_y += self.change_y

        self.anim_timer += delta_time
        if self.anim_timer > FLY_ANIMATION_SPEED:
            self.anim_timer = 0
            self.frame_index = 1 - self.frame_index

            look_direction = 0 if self.change_x > 0 else 1
            self.texture = self.anim_textures[self.frame_index][look_direction]


class PlayerCharacter(arcade.Sprite):
    def __init__(self):
        super().__init__()

        self.scale = 0.7
        self.cur_frame = 0
        self.anim_timer = 0
        self.face_direction = 1

        self.idle_texture_pair = get_texture_pair(ASSET_PLAYER)

        self.walk_textures = []
        for i in range(1, 12):
            texture_path = f"project3/p3_walk{i:02}.png"
            self.walk_textures.append(get_texture_pair(texture_path))
        self.texture = self.idle_texture_pair[1]

    def update_animation(self, delta_time: float = 1 / 60):
        if self.change_x < 0:
            self.face_direction = 0
        elif self.change_x > 0:
            self.face_direction = 1

        if self.change_x != 0:
            self.anim_timer += delta_time
            if self.anim_timer > PLAYER_ANIM_SPEED:
                self.anim_timer = 0
                self.cur_frame += 1
                if self.cur_frame >= len(self.walk_textures):
                    self.cur_frame = 0
            self.texture = self.walk_textures[self.cur_frame][self.face_direction]
        else:
            self.texture = self.idle_texture_pair[self.face_direction]


class BaseView(arcade.View):
    def display_message(self, text, y_pos, font_size, color):
        label = arcade.Text(text, self.window.width / 2, self.window.height / 2 + y_pos,
                            color, font_size, anchor_x="center",
                            multiline=True, width=self.window.width - 100, align="center")
        label.draw()


class MenuView(BaseView):
    def on_show_view(self):
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

    def on_draw(self):
        self.clear()
        self.display_message("ГЛАВНОЕ МЕНЮ\n\nENTER - Играть", 0, 35, arcade.color.WHITE)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game = GameView()
            game.setup()
            self.window.show_view(game)


class PauseView(BaseView):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        msg = "ПАУЗА\n\nESC или P - Продолжить\n\nM - Главное меню"
        self.pause_label = arcade.Text(msg, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                                       arcade.color.WHITE, 30, anchor_x="center",
                                       align="center", multiline=True, width=600)

    def on_draw(self):
        self.game_view.on_draw()
        arcade.draw_rect_filled(
            arcade.XYWH(self.window.width / 2, self.window.height / 2,
                        self.window.width, self.window.height),
            (0, 0, 0, 150)
        )

        self.pause_label.x = self.window.width / 2
        self.pause_label.y = self.window.height / 2
        self.pause_label.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE or key == arcade.key.P:
            self.window.show_view(self.game_view)
        elif key == arcade.key.M:
            self.game_view.stop_walk_sound()
            self.window.show_view(MenuView())


class GameOverView(BaseView):
    def __init__(self, death_count):
        super().__init__()
        self.death_count = death_count

    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        self.clear()
        info = f"ВЫ УМЕРЛИ\n\nСмертей: {self.death_count}\n\nENTER - Рестарт"
        self.display_message(info, 0, 25, arcade.color.RED)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game = GameView(self.death_count)
            game.setup()
            self.window.show_view(game)


class WinView(BaseView):
    def __init__(self, coins, jumps, deaths):
        super().__init__()
        self.session_data = (coins, jumps, deaths)
        DatabaseController().insert_session_stats(coins, jumps, deaths)

    def on_show_view(self):
        arcade.set_background_color(arcade.color.DARK_GREEN)

    def on_draw(self):
        self.clear()
        c, j, d = self.session_data
        info = f"ПОБЕДА!\n\nМонет: {c}\nСмертей: {d}\n\nENTER - В меню"
        self.display_message(info, 0, 25, arcade.color.GOLD)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            self.window.show_view(MenuView())


def toggle_music(window):
    if window.music_on:
        window.music_player.pause()
        window.music_on = False
    else:
        window.music_player.play()
        window.music_on = True


class GameView(arcade.View):
    def __init__(self, deaths=0):
        super().__init__()
        self.map_data = None
        self.player_sprite = None
        self.player_list = None
        self.coins_list = None
        self.enemies_list = None
        self.platforms_list = None
        self.ice_list = None
        self.engine = None
        self.coins_collected = 0
        self.jumps_made = 0
        self.deaths_total = deaths
        self.available_jumps = 0
        self.pressed_keys = {"left": False, "right": False, "up": False}
        self.cam_world = arcade.Camera2D()
        self.cam_gui = arcade.Camera2D()
        self.interface = HUD()

        self.walk_sound = None
        self.coin_sound = None
        self.walk_sound_player = None

    def on_resize(self, width: int, height: int):
        self.cam_world.viewport = (0, 0, width, height)
        self.cam_gui.viewport = (0, 0, width, height)
        self.cam_world.projection = (0, width, 0, height)
        self.cam_gui.projection = (0, width, 0, height)
        super().on_resize(width, height)

    def setup_level_map(self):
        self.map_data = arcade.load_tilemap(ASSET_MAP, TILE_SCALING)
        self.wall_list = self.map_data.sprite_lists.get("collisions", arcade.SpriteList())
        self.trap_list = self.map_data.sprite_lists.get("spikes", arcade.SpriteList())
        self.goal_list = self.map_data.sprite_lists.get("exit", arcade.SpriteList())
        self.ladder_list = self.map_data.sprite_lists.get("ladder", arcade.SpriteList())
        self.ice_list = self.map_data.sprite_lists.get("ice", arcade.SpriteList())

    def setup_player_character(self):
        self.player_list = arcade.SpriteList()
        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x, self.player_sprite.center_y = 950, 256
        self.player_list.append(self.player_sprite)

    def setup_collectables(self):
        self.coins_list = arcade.SpriteList()
        coordinates = [[1230, 1100], [470, 400], [1150, 1260]]
        for pos in coordinates:
            item = arcade.Sprite(ASSET_COIN, 1.0)
            item.center_x, item.center_y = pos[0], pos[1]
            self.coins_list.append(item)

    def setup_enemy_units(self):
        self.enemies_list = arcade.SpriteList()
        self.enemies_list.append(SnailEnemy(1150, 1200, 920, 1190))

    def setup_moving_objects(self):
        self.platforms_list = arcade.SpriteList()
        self.platforms_list.append(
            MovingPlatform(ASSET_PLATFORM, 0.9, 1000, 800, PLATFORM_LEFT_LIMIT, PLATFORM_RIGHT_LIMIT, PLATFORM_SPEED))

    def setup(self):
        arcade.set_background_color(arcade.color.SKY_BLUE)
        self.setup_level_map()
        self.setup_player_character()
        self.setup_collectables()
        self.setup_enemy_units()
        self.setup_moving_objects()

        self.walk_sound = arcade.load_sound(WALKING_SOUND)
        self.coin_sound = arcade.load_sound(COIN_SOUND)

        self.engine = arcade.PhysicsEnginePlatformer(self.player_sprite,
                                                     platforms=[self.wall_list, self.platforms_list, self.ice_list],
                                                     gravity_constant=GRAVITY, ladders=self.ladder_list)

    def on_draw(self):
        self.clear()
        self.cam_world.use()
        for layer in self.map_data.sprite_lists.values():
            layer.draw()
        self.coins_list.draw()
        self.enemies_list.draw()
        self.platforms_list.draw()
        self.player_list.draw()
        self.cam_gui.use()
        self.interface.draw()

    def sync_camera(self):
        tx, ty = self.player_sprite.center_x, self.player_sprite.center_y
        nx = arcade.math.lerp(self.cam_world.position.x, tx, CAMERA_SPEED)
        ny = arcade.math.lerp(self.cam_world.position.y, ty, CAMERA_SPEED)
        self.cam_world.position = (nx, ny)

    def stop_walk_sound(self):
        if self.walk_sound_player:
            arcade.stop_sound(self.walk_sound_player)
            self.walk_sound_player = None

    def check_collisions(self):

        for coin in arcade.check_for_collision_with_list(self.player_sprite, self.coins_list):
            coin.remove_from_sprite_lists()
            self.coins_collected += 1
            arcade.play_sound(self.coin_sound)

        if arcade.check_for_collision_with_list(self.player_sprite, self.enemies_list) or \
                arcade.check_for_collision_with_list(self.player_sprite, self.trap_list):
            self.deaths_total += 1
            self.stop_walk_sound()
            self.window.show_view(GameOverView(self.deaths_total))

        if arcade.check_for_collision_with_list(self.player_sprite, self.goal_list):
            self.stop_walk_sound()
            self.window.show_view(BetweenLevelsView(self.coins_collected, self.jumps_made, self.deaths_total))

    def on_update(self, delta_time: float):
        self.engine.update()
        self.platforms_list.update(delta_time)
        self.enemies_list.update(delta_time)
        self.player_list.update_animation(delta_time)

        if self.engine.can_jump():
            self.available_jumps = 2

        on_ice = arcade.check_for_collision_with_list(self.player_sprite, self.ice_list)
        active_speed = MOVEMENT_SPEED * ICE_SPEED_FACTOR if on_ice else MOVEMENT_SPEED

        self.player_sprite.change_x = (self.pressed_keys["right"] - self.pressed_keys["left"]) * active_speed


        is_moving = self.player_sprite.change_x != 0
        is_on_ground = self.engine.can_jump()

        if is_moving and is_on_ground:

            if not self.walk_sound_player or not self.walk_sound_player.playing:
                self.walk_sound_player = arcade.play_sound(self.walk_sound, loop=True)
        else:
        
            if self.walk_sound_player:
                arcade.stop_sound(self.walk_sound_player)
                self.walk_sound_player = None

        self.check_collisions()
        self.sync_camera()
        self.interface.update_text(self.coins_collected, self.deaths_total)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.N:
            toggle_music(self.window)
        if key == arcade.key.ESCAPE or key == arcade.key.P:
            self.stop_walk_sound()
            self.window.show_view(PauseView(self))
        elif key in (arcade.key.W, arcade.key.UP, arcade.key.SPACE):
            if self.available_jumps > 0:
                self.player_sprite.change_y = JUMP_STRENGTH
                self.available_jumps -= 1
                self.jumps_made += 1
            self.pressed_keys["up"] = True
        elif key in (arcade.key.A, arcade.key.LEFT):
            self.pressed_keys["left"] = True
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.pressed_keys["right"] = True

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.W, arcade.key.UP, arcade.key.SPACE):
            self.pressed_keys["up"] = False
        elif key in (arcade.key.A, arcade.key.LEFT):
            self.pressed_keys["left"] = False
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.pressed_keys["right"] = False


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
    window.bg_music = arcade.load_sound(ASSET_MUSIC)
    window.music_player = window.bg_music.play(volume=0.3, loop=True)
    window.music_on = True

    window.show_view(MenuView())
    arcade.run()


ASSET_MAP_LEVEL_2 = "project3/game67.tmx"


class Level2View(GameView):
    def __init__(self, deaths=0, coins=0):
        super().__init__(deaths)
        self.coins_collected = coins

    def setup_level_map(self):
        self.map_data = arcade.load_tilemap(ASSET_MAP_LEVEL_2, TILE_SCALING)
        self.wall_list = self.map_data.sprite_lists.get("collisions", arcade.SpriteList())
        self.trap_list = self.map_data.sprite_lists.get("spikes", arcade.SpriteList())
        self.goal_list = self.map_data.sprite_lists.get("exit", arcade.SpriteList())
        self.ladder_list = self.map_data.sprite_lists.get("ladder", arcade.SpriteList())
        self.ice_list = self.map_data.sprite_lists.get("ice", arcade.SpriteList())
        self.water_list = self.map_data.sprite_lists.get("water", arcade.SpriteList())

    def setup_player_character(self):
        self.player_list = arcade.SpriteList()
        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x = 200
        self.player_sprite.center_y = 520
        self.player_list.append(self.player_sprite)

    def setup_collectables(self):
        self.coins_list = arcade.SpriteList()

    def setup_enemy_units(self):
        self.enemies_list = arcade.SpriteList()
        fly_enemy = FlyingEnemy(800, 600, self.player_sprite)
        self.enemies_list.append(fly_enemy)

    def setup_moving_objects(self):
        self.platforms_list = arcade.SpriteList()

    def check_collisions(self):
        if arcade.check_for_collision_with_list(self.player_sprite, self.trap_list) or \
                arcade.check_for_collision_with_list(self.player_sprite, self.water_list) or \
                arcade.check_for_collision_with_list(self.player_sprite, self.enemies_list):
            self.deaths_total += 1
            self.stop_walk_sound()
            self.window.show_view(GameOverLevel2View(self.deaths_total))

        if arcade.check_for_collision_with_list(self.player_sprite, self.goal_list):
            self.stop_walk_sound()
            self.window.show_view(WinView(self.coins_collected, self.jumps_made, self.deaths_total))


class GameOverLevel2View(GameOverView):
    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game = Level2View(self.death_count)
            game.setup()
            self.window.show_view(game)


class BetweenLevelsView(BaseView):
    def __init__(self, coins, jumps, deaths):
        super().__init__()
        self.data = (coins, jumps, deaths)

    def on_show_view(self):
        arcade.set_background_color(arcade.color.DARK_SLATE_BLUE)

    def on_draw(self):
        self.clear()
        self.display_message("УРОВЕНЬ 1 ПРОЙДЕН!\n\nНажмите ENTER, чтобы начать Уровень 2", 0, 25, arcade.color.WHITE)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            lvl2 = Level2View(deaths=self.data[2], coins=self.data[0])
            lvl2.setup()
            self.window.show_view(lvl2)


class PauseView(BaseView):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        msg = "ПАУЗА\n\nESC или P - Продолжить\nM - Главное меню\nN - Вкл/Выкл музыку"
        self.pause_label = arcade.Text(msg, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                                       arcade.color.WHITE, 25, anchor_x="center",
                                       align="center", multiline=True, width=600)

    def on_draw(self):
        self.game_view.on_draw()
        arcade.draw_rect_filled(
            arcade.XYWH(self.window.width / 2, self.window.height / 2,
                        self.window.width, self.window.height),
            (0, 0, 0, 150)
        )
        self.pause_label.x = self.window.width / 2
        self.pause_label.y = self.window.height / 2
        self.pause_label.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE or key == arcade.key.P:
            self.window.show_view(self.game_view)
        elif key == arcade.key.M:
            self.game_view.stop_walk_sound()
            self.window.show_view(MenuView())
        elif key == arcade.key.N:
            toggle_music(self.window)


if __name__ == "__main__":
    main()
