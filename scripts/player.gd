extends CharacterBody2D
## 2.5D 城主: 2 walk rows × 8 frames, flip_h for 4 facings (SE / SW / NE / NW).

const WALK_SHEET := preload("res://assets/sprites/chengzhu_walk.png")
const SHEET_COLS := 8
const SHEET_ROWS := 2
const WALK_FPS := 10.0
const SPEED := 160.0
## Squash screen-Y so keyboard motion reads as a ~45° 2.5D ground plane.
const DEPTH_SCALE := 0.55

@export var map_size := Vector2(5120, 2880)
@export var map_margin := 40.0

@onready var sprite: AnimatedSprite2D = $AnimatedSprite2D

## +1 = south (front / SE-SW), -1 = north (back / NE-NW)
var _last_vertical := 1


func _ready() -> void:
	motion_mode = MOTION_MODE_FLOATING
	_build_sprite_frames()
	_apply_facing(Vector2.DOWN)
	sprite.play("idle_front")


func _physics_process(_delta: float) -> void:
	var input_dir := _read_move_vector()
	if input_dir.length_squared() > 1.0:
		input_dir = input_dir.normalized()

	var motion := Vector2(input_dir.x, input_dir.y * DEPTH_SCALE)
	velocity = motion * SPEED
	move_and_slide()
	global_position = global_position.clamp(
		Vector2(map_margin, map_margin),
		map_size - Vector2(map_margin, map_margin)
	)

	if input_dir.length_squared() > 0.0001:
		_apply_facing(input_dir)
		var walk := "walk_front" if _last_vertical >= 0 else "walk_back"
		if sprite.animation != walk or not sprite.is_playing():
			sprite.play(walk)
	else:
		var idle := "idle_front" if _last_vertical >= 0 else "idle_back"
		if sprite.animation != idle:
			sprite.play(idle)


func _read_move_vector() -> Vector2:
	# Prefer Input Map (WASD + arrows). Fall back to physical keys if the map is missing.
	if InputMap.has_action("move_left"):
		return Vector2(
			Input.get_axis("move_left", "move_right"),
			Input.get_axis("move_up", "move_down")
		)
	var x := 0.0
	var y := 0.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		x += 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		x -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		y += 1.0
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		y -= 1.0
	return Vector2(x, y)


func _apply_facing(dir: Vector2) -> void:
	if absf(dir.y) > 0.01:
		_last_vertical = 1 if dir.y > 0.0 else -1
	if dir.x < -0.01:
		sprite.flip_h = true  # SW / NW
	elif dir.x > 0.01:
		sprite.flip_h = false  # SE / NE
	# Pure north/south keeps the last east/west flip.


func _build_sprite_frames() -> void:
	var frames := SpriteFrames.new()
	var sheet: Texture2D = WALK_SHEET
	var frame_w := sheet.get_width() / SHEET_COLS
	var frame_h := sheet.get_height() / SHEET_ROWS

	# Origin at the feet so the chibi sits on the grass.
	sprite.centered = true
	sprite.offset = Vector2(0.0, -float(frame_h) * 0.5 + 12.0)

	for anim_name in ["walk_front", "walk_back", "idle_front", "idle_back"]:
		frames.add_animation(anim_name)
		frames.set_animation_loop(anim_name, anim_name.begins_with("walk"))
		frames.set_animation_speed(anim_name, WALK_FPS)

	for row in SHEET_ROWS:
		var walk_name := "walk_front" if row == 0 else "walk_back"
		var idle_name := "idle_front" if row == 0 else "idle_back"
		for col in SHEET_COLS:
			var atlas := AtlasTexture.new()
			atlas.atlas = sheet
			atlas.region = Rect2(col * frame_w, row * frame_h, frame_w, frame_h)
			atlas.filter_clip = true
			frames.add_frame(walk_name, atlas)
			if col == 0:
				frames.add_frame(idle_name, atlas)

	sprite.sprite_frames = frames
