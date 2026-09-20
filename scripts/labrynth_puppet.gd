class_name LabrynthPuppet
extends Node2D
## Cutout Skeleton2D rig for the Q-version 城主.
## Elbow / knee bones are separate so the walk cycle can bend those joints.

const RIG_PATH := "res://assets/labrynth/rig.json"

var walking := false
var facing_right := false
var phase := 0.0

var _rig: Dictionary = {}
var _base_scale := 0.78
var _bones: Dictionary = {}  # String -> Bone2D


func _ready() -> void:
	_rig = _load_rig()
	_base_scale = float(_rig.get("scale", 0.78))
	_build_skeleton()
	_apply_facing()
	_apply_pose(_pose_angles(0.0, false))


func set_walking(value: bool) -> void:
	walking = value


func set_facing_from_dir_x(dir_x: float) -> void:
	if dir_x > 0.01:
		facing_right = true
		_apply_facing()
	elif dir_x < -0.01:
		facing_right = false
		_apply_facing()


func _physics_process(delta: float) -> void:
	var hz := float(_rig["walk_hz"]) if walking else float(_rig["idle_hz"])
	phase = fposmod(phase + delta * TAU * hz, TAU)
	if not walking and absf(sin(phase)) < 0.02:
		# Keep idle phase moving so breath doesn't freeze at a peak.
		pass
	_apply_pose(_pose_angles(phase, walking))


func _apply_facing() -> void:
	var sx := -_base_scale if facing_right else _base_scale
	scale = Vector2(sx, _base_scale)


func _load_rig() -> Dictionary:
	var text := FileAccess.get_file_as_string(RIG_PATH)
	var parsed: Variant = JSON.parse_string(text)
	assert(parsed is Dictionary, "Labrynth rig.json missing or invalid")
	return parsed


func _build_skeleton() -> void:
	var skeleton := Skeleton2D.new()
	skeleton.name = "Skeleton2D"
	add_child(skeleton)

	var hip := _bone(skeleton, "Hip", Vector2(0.0, -float(_rig["hip_from_feet"])))
	var torso := _bone(hip, "Torso", _vec(_rig["offsets"]["torso"]))
	var head := _bone(torso, "Head", _vec(_rig["offsets"]["head"]))
	var skirt := _bone(hip, "Skirt", _vec(_rig["offsets"]["skirt"]))

	var upper_l := _bone(torso, "UpperArmL", _vec(_rig["offsets"]["shoulder_l"]))
	var lower_l := _bone(upper_l, "LowerArmL", _vec(_rig["joints"]["elbow_l"]))
	var sleeve_l := _bone(upper_l, "SleeveL", _vec(_rig["offsets"]["sleeve_l"]))

	var upper_r := _bone(torso, "UpperArmR", _vec(_rig["offsets"]["shoulder_r"]))
	var lower_r := _bone(upper_r, "LowerArmR", _vec(_rig["joints"]["elbow_r"]))
	var sleeve_r := _bone(upper_r, "SleeveR", _vec(_rig["offsets"]["sleeve_r"]))

	var thigh_l := _bone(hip, "ThighL", _vec(_rig["offsets"]["hip_l"]))
	var calf_l := _bone(thigh_l, "CalfL", _vec(_rig["joints"]["knee_l"]))
	var thigh_r := _bone(hip, "ThighR", _vec(_rig["offsets"]["hip_r"]))
	var calf_r := _bone(thigh_r, "CalfR", _vec(_rig["joints"]["knee_r"]))

	_attach_sprite(head, "head")
	_attach_sprite(torso, "torso")
	_attach_sprite(skirt, "skirt")
	_attach_sprite(sleeve_l, "sleeve_l")
	_attach_sprite(sleeve_r, "sleeve_r")
	_attach_sprite(upper_l, "upper_arm_l")
	_attach_sprite(lower_l, "forearm_l")
	_attach_sprite(upper_r, "upper_arm_r")
	_attach_sprite(lower_r, "forearm_r")
	_attach_sprite(thigh_l, "thigh_l")
	_attach_sprite(calf_l, "calf_l")
	_attach_sprite(thigh_r, "thigh_r")
	_attach_sprite(calf_r, "calf_r")

	for bone in _bones.values():
		var b := bone as Bone2D
		b.rest = b.transform


func _bone(parent: Node2D, bone_name: String, local_pos: Vector2) -> Bone2D:
	var bone := Bone2D.new()
	bone.name = bone_name
	bone.position = local_pos
	bone.auto_calculate_length_and_angle = false
	parent.add_child(bone)
	_bones[bone_name] = bone
	return bone


func _attach_sprite(bone: Bone2D, part_name: String) -> void:
	var spec: Dictionary = _rig["parts"][part_name]
	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = load(String(spec["file"])) as Texture2D
	sprite.centered = false
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	var pivot: Array = spec["pivot"]
	sprite.position = Vector2(-float(pivot[0]), -float(pivot[1]))
	sprite.z_as_relative = false
	sprite.z_index = int(spec["z"])
	bone.add_child(sprite)


func _pose_angles(p: float, moving: bool) -> Dictionary:
	var rest: Dictionary = _rig["rest"]
	var walk: Dictionary = _rig["walk"]
	if not moving:
		var breath := sin(p) * 1.2
		return {
			"hip_x": 0.0,
			"hip_y": breath * 0.4,
			"Hip": breath * 0.3,
			"Torso": -breath * 0.4,
			"Head": breath * 0.6,
			"Skirt": breath * 0.5,
			"ThighL": float(rest["thigh_l"]),
			"ThighR": float(rest["thigh_r"]),
			"CalfL": float(rest["calf_l"]),
			"CalfR": float(rest["calf_r"]),
			"UpperArmL": float(rest["arm_l"]),
			"UpperArmR": float(rest["arm_r"]),
			"LowerArmL": float(rest["elbow_l"]),
			"LowerArmR": float(rest["elbow_r"]),
			"SleeveL": 0.0,
			"SleeveR": 0.0,
		}
	var s := sin(p)
	var c := cos(p)
	var left_swing := maxf(0.0, -s)
	var right_swing := maxf(0.0, s)
	var thigh_swing := float(walk["thigh_swing"])
	var arm_swing := float(walk["arm_swing"])
	var knee_max := float(walk["knee_max"])
	return {
		"hip_x": s * float(walk["hip_x"]),
		"hip_y": absf(c) * float(walk["hip_bob"]),
		"Hip": s * float(walk["hip_sway"]),
		"Torso": -s * float(walk["torso_counter"]),
		"Head": -s * float(walk["head_counter"]),
		"Skirt": -s * float(walk["skirt_sway"]),
		"ThighL": float(rest["thigh_l"]) + c * thigh_swing,
		"ThighR": float(rest["thigh_r"]) - c * thigh_swing,
		"CalfL": float(rest["calf_l"]) + left_swing * knee_max,
		"CalfR": float(rest["calf_r"]) - right_swing * knee_max,
		"UpperArmL": float(rest["arm_l"]) + c * arm_swing,
		"UpperArmR": float(rest["arm_r"]) + c * arm_swing,
		"LowerArmL": float(rest["elbow_l"]) + left_swing * 10.0,
		"LowerArmR": float(rest["elbow_r"]) - right_swing * 10.0,
		"SleeveL": 0.0,
		"SleeveR": 0.0,
	}


func _apply_pose(angles: Dictionary) -> void:
	var hip: Bone2D = _bones["Hip"]
	hip.position = Vector2(float(angles["hip_x"]), -float(_rig["hip_from_feet"]) + float(angles["hip_y"]))
	hip.rotation_degrees = float(angles["Hip"])
	for bone_name in [
		"Torso", "Head", "Skirt",
		"ThighL", "ThighR", "CalfL", "CalfR",
		"UpperArmL", "UpperArmR", "LowerArmL", "LowerArmR",
		"SleeveL", "SleeveR",
	]:
		(_bones[bone_name] as Bone2D).rotation_degrees = float(angles[bone_name])


func _vec(arr: Variant) -> Vector2:
	var a: Array = arr
	return Vector2(float(a[0]), float(a[1]))
