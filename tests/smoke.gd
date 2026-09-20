extends Node
## Headless smoke test for the 2.5D mini demo.
## Run: godot --headless --path . res://tests/smoke.tscn

const MAIN_SCENE := "res://scenes/main.tscn"
const XIAOLV_SCENE := "res://scenes/xiaolv_skel_run.tscn"
const WALK_SHEET := "res://assets/sprites/chengzhu_walk.png"
const GRASS := "res://assets/textures/grass.png"
const XIAOLV_HEAD := "res://assets/sprites/xiaolv_parts/head.png"
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

	var sprite := player.get_node_or_null("AnimatedSprite2D") as AnimatedSprite2D
	var camera := player.get_node_or_null("Camera2D") as Camera2D
	_expect(sprite != null, "AnimatedSprite2D exists")
	_expect(camera != null, "Camera2D exists")
	if sprite == null or camera == null:
		return

	_expect(player.motion_mode == CharacterBody2D.MOTION_MODE_FLOATING, "player is MOTION_MODE_FLOATING")
	_expect(camera.enabled, "Camera2D.enabled is true")
	_expect(camera.is_current(), "Camera2D is current")
	_expect(is_equal_approx(camera.zoom.x, 1.25), "Camera2D zoom is 1.25")

	if floor_node != null:
		_expect(floor_node.get("texture") != null, "Floor texture is assigned")
		var area: Variant = floor_node.get("area_size")
		_expect(area == Vector2(5120, 2880), "Floor area_size is 5120x2880")

	var frames: SpriteFrames = sprite.sprite_frames
	_expect(frames != null, "SpriteFrames built")
	if frames != null:
		for anim in ["walk_front", "walk_back", "idle_front", "idle_back"]:
			_expect(frames.has_animation(anim), "has animation '%s'" % anim)
		_expect(frames.get_frame_count("walk_front") == 8, "walk_front has 8 frames")
		_expect(frames.get_frame_count("walk_back") == 8, "walk_back has 8 frames")
		_expect(frames.get_frame_count("idle_front") == 1, "idle_front has 1 frame")
		_expect(frames.get_frame_count("idle_back") == 1, "idle_back has 1 frame")

	_expect(sprite.animation == "idle_front", "starts idle_front (got '%s')" % sprite.animation)
	_expect(player.global_position.distance_to(Vector2(2560, 1440)) < 1.0, "spawns at map center")

	# SE: down-right → front, flip (sheet faces left)
	var origin := player.global_position
	await _hold_actions(["move_right", "move_down"], PHYSICS_FRAMES)
	_expect(player.global_position.x > origin.x + 8.0, "SE increases X")
	_expect(player.global_position.y > origin.y + 4.0, "SE increases Y")
	_expect(sprite.animation == "walk_front", "SE plays walk_front (got '%s')" % sprite.animation)
	_expect(sprite.is_playing(), "walk plays while moving")
	_expect(sprite.flip_h, "SE sets flip_h")

	# Idle after release
	await _wait_physics(PHYSICS_FRAMES)
	_expect(sprite.animation == "idle_front", "idle_front after SE stop (got '%s')" % sprite.animation)
	_expect(player.velocity.length() < 0.1, "velocity ~0 when idle")

	# SW: down-left → front, no flip
	origin = player.global_position
	await _hold_actions(["move_left", "move_down"], PHYSICS_FRAMES)
	_expect(player.global_position.x < origin.x - 8.0, "SW decreases X")
	_expect(sprite.animation == "walk_front", "SW plays walk_front")
	_expect(not sprite.flip_h, "SW does not flip_h")
	await _hold_actions([], 2)

	# NE: up-right → back, flip
	origin = player.global_position
	await _hold_actions(["move_right", "move_up"], PHYSICS_FRAMES)
	_expect(player.global_position.y < origin.y - 4.0, "NE decreases Y")
	_expect(player.global_position.x > origin.x + 8.0, "NE increases X")
	_expect(sprite.animation == "walk_back", "NE plays walk_back (got '%s')" % sprite.animation)
	_expect(sprite.flip_h, "NE sets flip_h")
	await _hold_actions([], 2)

	# NW: up-left → back, no flip
	origin = player.global_position
	await _hold_actions(["move_left", "move_up"], PHYSICS_FRAMES)
	_expect(player.global_position.x < origin.x - 8.0, "NW decreases X")
	_expect(sprite.animation == "walk_back", "NW plays walk_back")
	_expect(not sprite.flip_h, "NW does not flip_h")
	await _hold_actions([], 2)

	# Camera child follows player
	_expect(
		camera.global_position.distance_to(player.global_position) < 2.0,
		"Camera2D follows player"
	)

	# Map clamp: cannot walk past margin
	player.global_position = Vector2(10, 10)
	await _hold_actions(["move_left", "move_up"], PHYSICS_FRAMES)
	_expect(player.global_position.x >= 40.0 - 0.1, "X clamps at map_margin")
	_expect(player.global_position.y >= 40.0 - 0.1, "Y clamps at map_margin")
	await _hold_actions([], 1)

	# Physical WASD/arrows via InputEventKey (same path as a real keyboard)
	player.global_position = Vector2(2560, 1440)
	await _wait_physics(1)
	origin = player.global_position
	await _hold_physical([KEY_D], PHYSICS_FRAMES)
	_expect(player.global_position.x > origin.x + 8.0, "physical KEY_D moves right")
	await _hold_physical([KEY_RIGHT], PHYSICS_FRAMES)
	_expect(player.global_position.x > origin.x + 16.0, "physical KEY_RIGHT moves right")
	await _hold_physical([], 1)

	# 小绿 Skeleton2D run lives in a second scene so 城主 main.tscn stays intact.
	main.queue_free()
	await _wait_physics(1)
	await _run_xiaolv()


func _check_assets() -> void:
	var sheet: Texture2D = load(WALK_SHEET)
	_expect(sheet != null, "walk sheet loads")
	if sheet != null:
		_expect(sheet.get_width() == 1280, "walk sheet width is 1280")
		_expect(sheet.get_height() == 720, "walk sheet height is 720")
	var grass: Texture2D = load(GRASS)
	_expect(grass != null, "grass texture loads")
	if grass != null:
		_expect(grass.get_width() == 1280, "grass width is 1280")
		_expect(grass.get_height() == 720, "grass height is 720")
	var head: Texture2D = load(XIAOLV_HEAD)
	_expect(head != null, "xiaolv head part loads")
	if head != null:
		_expect(head.get_width() > 32, "xiaolv head has width")


func _run_xiaolv() -> void:
	var packed: PackedScene = load(XIAOLV_SCENE)
	_expect(packed != null, "xiaolv_skel_run scene loads")
	if packed == null:
		return

	var root: Node = packed.instantiate()
	add_child(root)
	await _wait_physics(2)

	var xiaolv := root.get_node_or_null("Xiaolv") as CharacterBody2D
	_expect(xiaolv != null, "Xiaolv CharacterBody2D exists")
	if xiaolv == null:
		return

	var skel := xiaolv.find_child("Skeleton2D", true, false) as Skeleton2D
	_expect(skel != null, "Skeleton2D exists")
	var ap := xiaolv.find_child("AnimationPlayer", true, false) as AnimationPlayer
	_expect(ap != null, "AnimationPlayer exists")
	if skel == null or ap == null:
		return

	var bone_names := [
		"Hips", "Spine", "Head",
		"ThighNear", "ShinNear", "ThighFar", "ShinFar",
		"ArmNear", "ForearmNear", "ArmFar", "ForearmFar",
		"Wing", "TailA", "TailB", "TailC",
	]
	var bone_count := _count_bones(skel)
	_expect(bone_count >= 15, "Skeleton2D has >= 15 Bone2D (got %d)" % bone_count)
	for bname in bone_names:
		var bone := skel.find_child(bname, true, false) as Bone2D
		_expect(bone != null, "Bone2D '%s' exists" % bname)

	_expect(ap.has_animation("xiaolv/run"), "has animation xiaolv/run")
	_expect(ap.is_playing(), "run autoplays")
	_expect(ap.current_animation == "xiaolv/run", "current animation is xiaolv/run (got '%s')" % ap.current_animation)

	if ap.has_animation("xiaolv/run"):
		var anim: Animation = ap.get_animation("xiaolv/run")
		_expect(anim.loop_mode == Animation.LOOP_LINEAR, "run loops")
		_expect(anim.get_track_count() >= 8, "run has >= 8 tracks (got %d)" % anim.get_track_count())
		if anim.get_track_count() > 0:
			_expect(
				anim.track_get_key_count(0) >= 8,
				"run track 0 has >= 8 keys (got %d)" % anim.track_get_key_count(0)
			)

	var sprites := _count_sprites(skel)
	_expect(sprites >= 10, "cutout Sprite2D pieces parented to bones (got %d)" % sprites)

	var thigh := skel.find_child("ThighNear", true, false) as Bone2D
	if thigh != null:
		var r0 := thigh.rotation
		await get_tree().create_timer(0.25).timeout
		_expect(not is_equal_approx(thigh.rotation, r0), "ThighNear rotation changes during run")

	# Left-facing default; move right flips; run keeps playing (skeletal, not frames).
	_expect(xiaolv.global_position.distance_to(Vector2(2560, 1440)) < 1.0, "xiaolv spawns at map center")
	var facing := xiaolv.get_node_or_null("Facing") as Node2D
	_expect(facing != null, "Facing node exists")
	if facing != null:
		_expect(facing.scale.x > 0.0, "default facing is left (+scale.x)")
		var origin := xiaolv.global_position
		await _hold_actions(["move_right"], PHYSICS_FRAMES)
		_expect(xiaolv.global_position.x > origin.x + 8.0, "xiaolv moves right")
		_expect(facing.scale.x < 0.0, "move right flips facing (scale.x < 0)")
		_expect(ap.is_playing(), "run keeps playing while moving")
		await _hold_actions(["move_left"], PHYSICS_FRAMES)
		_expect(facing.scale.x > 0.0, "move left faces left again")
		await _hold_actions([], 1)

	root.queue_free()
	await _wait_physics(1)


func _count_bones(n: Node) -> int:
	var c := 1 if n is Bone2D else 0
	for child in n.get_children():
		c += _count_bones(child)
	return c


func _count_sprites(n: Node) -> int:
	var c := 1 if n is Sprite2D else 0
	for child in n.get_children():
		c += _count_sprites(child)
	return c


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
