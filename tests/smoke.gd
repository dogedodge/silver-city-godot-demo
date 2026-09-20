extends Node
## Headless smoke test for the 2.5D skeletal walk demo.
## Run: godot --headless --path . res://tests/smoke.tscn

const MAIN_SCENE := "res://scenes/main.tscn"
const RIG := "res://assets/labrynth/rig.json"
const GRASS := "res://assets/textures/grass.png"
const HEAD_TEX := "res://assets/labrynth/parts/head.png"
const PHYSICS_FRAMES := 20

var _failures: PackedStringArray = []


func _ready() -> void:
	await _run()
	if _failures.is_empty():
		print("SMOKE TEST PASSED")
		get_tree().quit(0)
	else:
		print("SMOKE TEST FAILED (%d)" % _failures.size())
		for f in _failures:
			print("  - ", f)
		get_tree().quit(1)


func _run() -> void:
	_check_assets()
	var packed: PackedScene = load(MAIN_SCENE)
	_expect(packed != null, "main scene loads")
	if packed == null:
		return

	var main: Node = packed.instantiate()
	add_child(main)
	await _wait_physics(2)

	var player := main.get_node_or_null("Player") as CharacterBody2D
	var floor_node := main.get_node_or_null("Floor") as Node2D
	_expect(player != null, "Player CharacterBody2D exists")
	_expect(floor_node != null, "Floor node exists")
	if player == null:
		return

	var puppet := player.get_node_or_null("Puppet") as Node2D
	var camera := player.get_node_or_null("Camera2D") as Camera2D
	_expect(puppet != null, "Puppet node exists")
	_expect(camera != null, "Camera2D exists")
	if puppet == null or camera == null:
		return

	_expect(player.motion_mode == CharacterBody2D.MOTION_MODE_FLOATING, "player is MOTION_MODE_FLOATING")
	_expect(camera.enabled, "Camera2D.enabled is true")
	_expect(camera.is_current(), "Camera2D is current")
	_expect(is_equal_approx(camera.zoom.x, 1.25), "Camera2D zoom is 1.25")

	if floor_node != null:
		_expect(floor_node.get("texture") != null, "Floor texture is assigned")
		var area: Variant = floor_node.get("area_size")
		_expect(area == Vector2(5120, 2880), "Floor area_size is 5120x2880")

	var skeleton := puppet.get_node_or_null("Skeleton2D") as Skeleton2D
	_expect(skeleton != null, "Skeleton2D exists")
	if skeleton == null:
		return

	for path in [
		"Hip",
		"Hip/Torso",
		"Hip/Torso/Head",
		"Hip/Torso/UpperArmL",
		"Hip/Torso/UpperArmL/LowerArmL",
		"Hip/Torso/UpperArmR",
		"Hip/Torso/UpperArmR/LowerArmR",
		"Hip/ThighL",
		"Hip/ThighL/CalfL",
		"Hip/ThighR",
		"Hip/ThighR/CalfR",
		"Hip/Skirt",
	]:
		var bone := skeleton.get_node_or_null(path)
		_expect(bone is Bone2D, "bone '%s' is Bone2D" % path)

	_expect(puppet.get("walking") == false, "starts idle (not walking)")
	_expect(player.global_position.distance_to(Vector2(2560, 1440)) < 1.0, "spawns at map center")

	var thigh_l := skeleton.get_node("Hip/ThighL") as Bone2D
	var calf_l := skeleton.get_node("Hip/ThighL/CalfL") as Bone2D
	var rest_thigh := thigh_l.rotation_degrees
	var rest_calf := calf_l.rotation_degrees

	# SE: down-right → walk, flip to face right
	var origin := player.global_position
	var phase0: float = float(puppet.get("phase"))
	await _hold_actions(["move_right", "move_down"], PHYSICS_FRAMES)
	_expect(player.global_position.x > origin.x + 8.0, "SE increases X")
	_expect(player.global_position.y > origin.y + 4.0, "SE increases Y")
	_expect(puppet.get("walking") == true, "SE sets walking")
	_expect(puppet.get("facing_right") == true, "SE faces right")
	_expect(puppet.scale.x < 0.0, "SE flips puppet scale.x")
	_expect(not is_equal_approx(float(puppet.get("phase")), phase0), "walk phase advances")

	# Elbow / knee actually change during the cycle.
	await _hold_actions(["move_right", "move_down"], 40)
	var moved_joint := (
		absf(thigh_l.rotation_degrees - rest_thigh) > 0.5
		or absf(calf_l.rotation_degrees - rest_calf) > 0.5
	)
	_expect(moved_joint, "thigh or knee rotation changes while walking")

	# Idle after release
	await _wait_physics(PHYSICS_FRAMES)
	_expect(puppet.get("walking") == false, "idle after SE stop")
	_expect(player.velocity.length() < 0.1, "velocity ~0 when idle")

	# SW: down-left → walk, native (no flip)
	origin = player.global_position
	await _hold_actions(["move_left", "move_down"], PHYSICS_FRAMES)
	_expect(player.global_position.x < origin.x - 8.0, "SW decreases X")
	_expect(puppet.get("walking") == true, "SW sets walking")
	_expect(puppet.get("facing_right") == false, "SW faces left")
	_expect(puppet.scale.x > 0.0, "SW does not flip scale.x")
	await _hold_actions([], 2)

	# NE: up-right → still the skeletal walk, face right
	origin = player.global_position
	await _hold_actions(["move_right", "move_up"], PHYSICS_FRAMES)
	_expect(player.global_position.y < origin.y - 4.0, "NE decreases Y")
	_expect(player.global_position.x > origin.x + 8.0, "NE increases X")
	_expect(puppet.get("walking") == true, "NE sets walking")
	_expect(puppet.get("facing_right") == true, "NE faces right")
	await _hold_actions([], 2)

	# NW: up-left
	origin = player.global_position
	await _hold_actions(["move_left", "move_up"], PHYSICS_FRAMES)
	_expect(player.global_position.x < origin.x - 8.0, "NW decreases X")
	_expect(puppet.get("walking") == true, "NW sets walking")
	_expect(puppet.get("facing_right") == false, "NW faces left")
	await _hold_actions([], 2)

	_expect(
		camera.global_position.distance_to(player.global_position) < 2.0,
		"Camera2D follows player"
	)

	player.global_position = Vector2(10, 10)
	await _hold_actions(["move_left", "move_up"], PHYSICS_FRAMES)
	_expect(player.global_position.x >= 40.0 - 0.1, "X clamps at map_margin")
	_expect(player.global_position.y >= 40.0 - 0.1, "Y clamps at map_margin")
	await _hold_actions([], 1)

	player.global_position = Vector2(2560, 1440)
	await _wait_physics(1)
	origin = player.global_position
	await _hold_physical([KEY_D], PHYSICS_FRAMES)
	_expect(player.global_position.x > origin.x + 8.0, "physical KEY_D moves right")
	await _hold_physical([KEY_RIGHT], PHYSICS_FRAMES)
	_expect(player.global_position.x > origin.x + 16.0, "physical KEY_RIGHT moves right")
	await _hold_physical([], 1)


func _check_assets() -> void:
	var rig_text := FileAccess.get_file_as_string(RIG)
	_expect(not rig_text.is_empty(), "rig.json loads")
	var grass: Texture2D = load(GRASS)
	_expect(grass != null, "grass texture loads")
	if grass != null:
		_expect(grass.get_width() == 1280, "grass width is 1280")
		_expect(grass.get_height() == 720, "grass height is 720")
	var head: Texture2D = load(HEAD_TEX)
	_expect(head != null, "head part texture loads")
	for part in [
		"torso", "skirt", "upper_arm_l", "forearm_l", "upper_arm_r", "forearm_r",
		"thigh_l", "calf_l", "thigh_r", "calf_r", "sleeve_l", "sleeve_r",
	]:
		var tex: Texture2D = load("res://assets/labrynth/parts/%s.png" % part)
		_expect(tex != null, "part '%s' loads" % part)


func _hold_actions(actions: Array, frames: int) -> void:
	for action in ["move_left", "move_right", "move_up", "move_down"]:
		if Input.is_action_pressed(action):
			Input.action_release(action)
	for action in actions:
		Input.action_press(action)
	await _wait_physics(frames)
	for action in actions:
		Input.action_release(action)


func _hold_physical(keys: Array, frames: int) -> void:
	for key in [KEY_W, KEY_A, KEY_S, KEY_D, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]:
		_emit_key(key, false)
	for key in keys:
		_emit_key(key, true)
	await _wait_physics(frames)
	for key in keys:
		_emit_key(key, false)


func _emit_key(physical: Key, pressed: bool) -> void:
	var ev := InputEventKey.new()
	ev.device = -1
	ev.pressed = pressed
	ev.physical_keycode = physical
	ev.keycode = physical
	ev.echo = false
	Input.parse_input_event(ev)
	Input.flush_buffered_events()


func _wait_physics(n: int) -> void:
	for _i in n:
		await get_tree().physics_frame


func _expect(cond: bool, message: String) -> void:
	if cond:
		print("  ok  ", message)
	else:
		_failures.append(message)
		print("  FAIL ", message)
