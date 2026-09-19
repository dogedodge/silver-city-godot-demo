extends CharacterBody2D
## 小绿 (Xiaolv) — Godot 4 Skeleton2D cutout puppet with an 8-key side-view run.
## Bones drive Sprite2D pieces (not SpriteFrames). Opens looping, facing left (−X).

const PARTS_DIR := "res://assets/sprites/xiaolv_parts"
const PARTS_JSON := "res://assets/sprites/xiaolv_parts/parts.json"
const RUN_FPS := 10.0
const POSE_COUNT := 8
const SPEED := 160.0
const DEPTH_SCALE := 0.55

@export var map_size := Vector2(5120, 2880)
@export var map_margin := 40.0
@export var autoplay_run := true

var _facing: Node2D
var _skeleton: Skeleton2D
var _anim_player: AnimationPlayer
var _bones: Dictionary = {}  # name -> Bone2D
var _rest_rot: Dictionary = {}  # name -> float
var _parts: Dictionary = {}
var _face_left := true

## Character-space joints (hips at origin, Y down, facing −X). Matches tools/paint_xiaolv_parts.py.
const L := {
	"hips": Vector2(0, 0),
	"neck": Vector2(0, -74),
	"crown": Vector2(4, -150),
	"shoulder": Vector2(-4, -58),
	"elbow": Vector2(-10, -16),
	"hand": Vector2(-18, 22),
	"hip_joint": Vector2(0, 6),
	"knee": Vector2(-2, 52),
	"ankle": Vector2(-4, 100),
	"wing_root": Vector2(18, -52),
	"wing_tip": Vector2(56, -64),
	"tail0": Vector2(20, 8),
	"tail1": Vector2(52, 2),
	"tail2": Vector2(80, -18),
	"tail3": Vector2(98, -46),
}


func _ready() -> void:
	motion_mode = MOTION_MODE_FLOATING
	_parts = _load_parts()
	_build_rig()
	_build_run_animation()
	if autoplay_run:
		_anim_player.play("xiaolv/run")


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

	if absf(input_dir.x) > 0.01:
		_face_left = input_dir.x < 0.0
		_facing.scale.x = 1.0 if _face_left else -1.0


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


func _load_parts() -> Dictionary:
	var txt := FileAccess.get_file_as_string(PARTS_JSON)
	var parsed: Variant = JSON.parse_string(txt)
	if typeof(parsed) == TYPE_DICTIONARY:
		return parsed
	push_warning("xiaolv: parts.json missing or invalid; using empty pivots")
	return {}


func _tex(name: String) -> Texture2D:
	return load(PARTS_DIR + "/" + name + ".png") as Texture2D


func _pivot(name: String) -> Vector2:
	if _parts.has(name) and _parts[name] is Dictionary and _parts[name].has("pivot"):
		var p: Array = _parts[name]["pivot"]
		return Vector2(float(p[0]), float(p[1]))
	return Vector2.ZERO


func _build_rig() -> void:
	_facing = Node2D.new()
	_facing.name = "Facing"
	add_child(_facing)

	_skeleton = Skeleton2D.new()
	_skeleton.name = "Skeleton2D"
	_facing.add_child(_skeleton)

	# Feet sit on the CharacterBody2D origin (grass). Hips live in character-space (0,0).
	var foot_y := L.ankle.y + 12.0
	var hips := Bone2D.new()
	hips.name = "Hips"
	hips.set_autocalculate_length_and_angle(false)
	_skeleton.add_child(hips)
	hips.position = Vector2(0.0, -foot_y)
	hips.rotation = 0.0
	hips.set_autocalculate_length_and_angle(false)
	hips.set_length(24.0)
	hips.set_bone_angle(0.0)
	hips.set_meta("cs_origin", Vector2.ZERO)
	_bones["Hips"] = hips

	_add_bone("Spine", hips, L.hips, L.neck)
	_add_bone("Head", _bones["Spine"], L.neck, L.crown)

	_add_bone("ThighFar", hips, L.hip_joint + Vector2(8, 1), L.knee + Vector2(8, 2))
	_add_bone("ShinFar", _bones["ThighFar"], L.knee + Vector2(8, 2), L.ankle + Vector2(8, 2))
	_add_bone("ThighNear", hips, L.hip_joint + Vector2(-6, 0), L.knee + Vector2(-6, 0))
	_add_bone("ShinNear", _bones["ThighNear"], L.knee + Vector2(-6, 0), L.ankle + Vector2(-8, 0))

	_add_bone("ArmFar", _bones["Spine"], L.shoulder + Vector2(10, 2), L.elbow + Vector2(10, 4))
	_add_bone("ForearmFar", _bones["ArmFar"], L.elbow + Vector2(10, 4), L.hand + Vector2(10, 4))
	_add_bone("ArmNear", _bones["Spine"], L.shoulder + Vector2(-6, 0), L.elbow + Vector2(-8, 0))
	_add_bone("ForearmNear", _bones["ArmNear"], L.elbow + Vector2(-8, 0), L.hand + Vector2(-10, 0))

	_add_bone("Wing", _bones["Spine"], L.wing_root, L.wing_tip)
	_add_bone("TailA", hips, L.tail0, L.tail1)
	_add_bone("TailB", _bones["TailA"], L.tail1, L.tail2)
	_add_bone("TailC", _bones["TailB"], L.tail2, L.tail3)

	_apply_rest(hips)

	var far := Color(0.78, 0.78, 0.84, 1.0)
	_attach("torso", _bones["Spine"], 0)
	_attach("head", _bones["Head"], 6)
	_attach("thigh", _bones["ThighFar"], -3, far)
	_attach("shin", _bones["ShinFar"], -2, far)
	_attach("thigh", _bones["ThighNear"], 1)
	_attach("shin", _bones["ShinNear"], 2)
	_attach("upper_arm", _bones["ArmFar"], -6, far)
	_attach("forearm", _bones["ForearmFar"], -5, far)
	_attach("upper_arm", _bones["ArmNear"], 4)
	_attach("forearm", _bones["ForearmNear"], 5)
	_attach("wing", _bones["Wing"], -4)
	_attach("tail_a", _bones["TailA"], -1)
	_attach("tail_b", _bones["TailB"], -1)
	_attach("tail_c", _bones["TailC"], -1)

	for name in _bones:
		_rest_rot[name] = (_bones[name] as Bone2D).rotation


func _add_bone(bname: String, parent: Bone2D, origin_cs: Vector2, distal_cs: Vector2) -> Bone2D:
	var bone := Bone2D.new()
	bone.name = bname
	bone.set_autocalculate_length_and_angle(false)
	parent.add_child(bone)
	var delta := distal_cs - origin_cs
	var angle := 0.0 if delta.length_squared() < 0.001 else delta.angle()
	var parent_origin := _bone_origin_cs(parent)
	var parent_angle := _bone_world_rot(parent)
	var rel := origin_cs - parent_origin
	bone.position = rel.rotated(-parent_angle)
	bone.rotation = wrapf(angle - parent_angle, -PI, PI)
	bone.set_length(maxf(delta.length(), 8.0))
	bone.set_bone_angle(0.0)
	_bones[bname] = bone
	bone.set_meta("cs_origin", origin_cs)
	return bone


func _bone_origin_cs(bone: Bone2D) -> Vector2:
	return bone.get_meta("cs_origin") as Vector2


func _bone_world_rot(bone: Bone2D) -> float:
	var r := 0.0
	var n: Node = bone
	while n is Bone2D:
		r += (n as Bone2D).rotation
		n = n.get_parent()
	return r


func _apply_rest(bone: Bone2D) -> void:
	bone.rest = bone.transform
	for child in bone.get_children():
		if child is Bone2D:
			_apply_rest(child)


func _attach(part: String, bone: Bone2D, z: int, modulate := Color.WHITE) -> void:
	var tex := _tex(part)
	if tex == null:
		push_warning("xiaolv: missing texture %s" % part)
		return
	var s := Sprite2D.new()
	s.name = part.capitalize().replace(" ", "") + "Sprite"
	s.texture = tex
	s.centered = false
	s.position = -_pivot(part)
	s.rotation = 0.0
	s.z_index = z
	s.z_as_relative = false
	s.modulate = modulate
	s.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	bone.add_child(s)


func _build_run_animation() -> void:
	_anim_player = AnimationPlayer.new()
	_anim_player.name = "AnimationPlayer"
	add_child(_anim_player)

	var anim := Animation.new()
	anim.loop_mode = Animation.LOOP_LINEAR
	anim.length = float(POSE_COUNT) / RUN_FPS
	anim.step = 1.0 / RUN_FPS

	# Extra rotation (radians added to rest). +clockwise. Legs: − = forward (facing left).
	# Contact → Down → Passing → Up × 2 (near / far phase offset).
	var thigh_n := _deg([-55, -28, 12, 58, 50, 22, -16, -58])
	var thigh_f := _deg([50, 22, -16, -58, -55, -28, 12, 58])
	var shin_n := _deg([12, 36, 58, 22, 16, 42, 10, 18])
	var shin_f := _deg([16, 42, 10, 18, 12, 36, 58, 22])
	var arm_n := _deg([38, 48, -8, -40, -36, -46, 12, 42])
	var arm_f := _deg([-36, -46, 12, 42, 38, 48, -8, -40])
	var forearm_n := _deg([14, 20, 6, 12, 12, 18, 8, 14])
	var forearm_f := _deg([12, 18, 8, 14, 14, 20, 6, 12])
	var spine := _deg([-6, -10, -4, -8, -6, -10, -4, -8])
	var head := _deg([3, 6, 2, 4, 3, 6, 2, 4])
	var wing := _deg([-8, 12, 2, -14, -8, 12, 2, -14])
	var tail_a := _deg([12, 4, -12, -4, 12, 4, -12, -4])
	var tail_b := _deg([8, -6, -10, 6, 8, -6, -10, 6])
	var tail_c := _deg([10, -8, -6, 8, 10, -8, -6, 8])
	var hip_y := [2.0, 6.0, 0.0, -5.0, 2.0, 6.0, 0.0, -5.0]

	_rot_track(anim, "Hips/Spine", "Spine", spine)
	_rot_track(anim, "Hips/Spine/Head", "Head", head)
	_rot_track(anim, "Hips/ThighNear", "ThighNear", thigh_n)
	_rot_track(anim, "Hips/ThighNear/ShinNear", "ShinNear", shin_n)
	_rot_track(anim, "Hips/ThighFar", "ThighFar", thigh_f)
	_rot_track(anim, "Hips/ThighFar/ShinFar", "ShinFar", shin_f)
	_rot_track(anim, "Hips/Spine/ArmNear", "ArmNear", arm_n)
	_rot_track(anim, "Hips/Spine/ArmNear/ForearmNear", "ForearmNear", forearm_n)
	_rot_track(anim, "Hips/Spine/ArmFar", "ArmFar", arm_f)
	_rot_track(anim, "Hips/Spine/ArmFar/ForearmFar", "ForearmFar", forearm_f)
	_rot_track(anim, "Hips/Spine/Wing", "Wing", wing)
	_rot_track(anim, "Hips/TailA", "TailA", tail_a)
	_rot_track(anim, "Hips/TailA/TailB", "TailB", tail_b)
	_rot_track(anim, "Hips/TailA/TailB/TailC", "TailC", tail_c)

	var hips_path := NodePath("Facing/Skeleton2D/Hips:position")
	var t := anim.add_track(Animation.TYPE_VALUE)
	anim.track_set_path(t, hips_path)
	anim.track_set_interpolation_type(t, Animation.INTERPOLATION_CUBIC)
	anim.track_set_interpolation_loop_wrap(t, true)
	var hips_rest: Vector2 = _bones["Hips"].position
	var dt := 1.0 / RUN_FPS
	for i in POSE_COUNT:
		anim.track_insert_key(t, i * dt, hips_rest + Vector2(0, hip_y[i]))
	anim.track_insert_key(t, anim.length, hips_rest + Vector2(0, hip_y[0]))

	var lib := AnimationLibrary.new()
	lib.add_animation("run", anim)
	_anim_player.add_animation_library("xiaolv", lib)


func _rot_track(anim: Animation, bone_path: String, bone_name: String, extras: Array) -> void:
	var path := NodePath("Facing/Skeleton2D/%s:rotation" % bone_path)
	var t := anim.add_track(Animation.TYPE_VALUE)
	anim.track_set_path(t, path)
	anim.track_set_interpolation_type(t, Animation.INTERPOLATION_CUBIC)
	anim.track_set_interpolation_loop_wrap(t, true)
	var rest: float = _rest_rot[bone_name]
	var dt := 1.0 / RUN_FPS
	for i in POSE_COUNT:
		anim.track_insert_key(t, i * dt, rest + extras[i])
	anim.track_insert_key(t, anim.length, rest + extras[0])


func _deg(values: Array) -> Array:
	var out: Array = []
	for d in values:
		out.append(deg_to_rad(float(d)))
	return out
