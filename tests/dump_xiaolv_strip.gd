extends Node2D
## Dumps an 8-pose run strip. Run:
##   godot --path . res://tests/dump_xiaolv_strip.tscn
## Writes /tmp/xiaolv_run_strip.png and quits.

const OUT := "/tmp/xiaolv_run_strip.png"
const POSES := 8
const DT := 0.1


func _ready() -> void:
	RenderingServer.set_default_clear_color(Color(0.97, 0.96, 0.94, 1.0))
	var packed: PackedScene = load("res://scenes/xiaolv.tscn")
	for i in POSES:
		var xiaolv: CharacterBody2D = packed.instantiate()
		xiaolv.autoplay_run = false
		xiaolv.position = Vector2(90.0 + float(i) * 150.0, 300.0)
		xiaolv.scale = Vector2(1.25, 1.25)
		add_child(xiaolv)
		var cam := xiaolv.get_node_or_null("Camera2D") as Camera2D
		if cam != null:
			cam.enabled = false
		await get_tree().process_frame
		var ap := xiaolv.get_node("AnimationPlayer") as AnimationPlayer
		ap.play("xiaolv/run")
		ap.seek(float(i) * DT, true)
		ap.pause()

	var camera := Camera2D.new()
	camera.position = Vector2(640, 240)
	camera.enabled = true
	add_child(camera)

	await get_tree().process_frame
	await get_tree().process_frame
	var img := get_viewport().get_texture().get_image()
	var err := img.save_png(OUT)
	if err != OK:
		push_error("Failed to save strip: %s" % error_string(err))
		print("DUMP STRIP FAILED")
		get_tree().quit(1)
		return
	print("DUMP STRIP WROTE ", OUT)
	get_tree().quit(0)
