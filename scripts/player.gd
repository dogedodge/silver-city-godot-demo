extends CharacterBody2D
## 2.5D 城主 with a cutout Skeleton2D walk (elbow / knee bones).
## Native art faces the camera in 3/4; scale.x flips for east vs west.

const SPEED := 160.0
## Squash screen-Y so keyboard motion reads as a ~45° 2.5D ground plane.
const DEPTH_SCALE := 0.55

@export var map_size := Vector2(5120, 2880)
@export var map_margin := 40.0

@onready var puppet: LabrynthPuppet = $Puppet


func _ready() -> void:
	motion_mode = MOTION_MODE_FLOATING
	puppet.set_walking(false)


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
		puppet.set_facing_from_dir_x(input_dir.x)
		puppet.set_walking(true)
	else:
		puppet.set_walking(false)


func _read_move_vector() -> Vector2:
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
