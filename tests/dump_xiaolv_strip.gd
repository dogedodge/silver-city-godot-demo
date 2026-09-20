extends Node2D
## Dumps an 8-pose run strip with wide cells and padding so horns/tail/boots stay in frame.
##   godot --path . res://tests/dump_xiaolv_strip.tscn
## Writes /tmp/xiaolv_run_strip.png and quits.

const OUT := "/tmp/xiaolv_run_strip.png"
const POSES := 8
const DT := 0.1
const CELL_W := 280.0
const PAD := 60.0
const STRIP_H := 540.0
const GROUND_Y := 400.0


func _ready() -> void:
	RenderingServer.set_default_clear_color(Color(0.97, 0.96, 0.94, 1.0))
	var strip_w := int(PAD * 2.0 + CELL_W * float(POSES))
	var strip_h := int(STRIP_H)

	var win := get_window()
	win.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	win.size = Vector2i(strip_w, strip_h)
	DisplayServer.window_set_size(Vector2i(strip_w, strip_h))

	var sv := SubViewport.new()
	sv.size = Vector2i(strip_w, strip_h)
	sv.transparent_bg = false
	sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	sv.disable_3d = true
	sv.snap_2d_transforms_to_pixel = false
	sv.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_LINEAR
	add_child(sv)

	var bg := ColorRect.new()
	bg.color = Color(0.97, 0.96, 0.94, 1.0)
	bg.size = Vector2(strip_w, strip_h)
	sv.add_child(bg)

	var world := Node2D.new()
	sv.add_child(world)

	var packed: PackedScene = load("res://scenes/xiaolv.tscn")
	for i in POSES:
		var xiaolv: CharacterBody2D = packed.instantiate()
		xiaolv.autoplay_run = false
		xiaolv.position = Vector2(PAD + CELL_W * 0.5 + float(i) * CELL_W, GROUND_Y)
		xiaolv.scale = Vector2(1.0, 1.0)
		world.add_child(xiaolv)
		var old_cam := xiaolv.get_node_or_null("Camera2D") as Camera2D
		if old_cam != null:
			old_cam.enabled = false
		await get_tree().process_frame
		var ap := xiaolv.get_node("AnimationPlayer") as AnimationPlayer
		ap.play("xiaolv/run")
		ap.seek(float(i) * DT, true)
		ap.pause()

	var camera := Camera2D.new()
	camera.position = Vector2(float(strip_w) * 0.5, float(strip_h) * 0.5)
	camera.zoom = Vector2.ONE
	sv.add_child(camera)
	camera.enabled = true
	camera.make_current()

	await get_tree().process_frame
	await get_tree().process_frame
	await get_tree().process_frame

	var img := sv.get_texture().get_image()
	var err := img.save_png(OUT)
	if err != OK:
		push_error("Failed to save strip: %s" % error_string(err))
		print("DUMP STRIP FAILED")
		get_tree().quit(1)
		return
	print("DUMP STRIP WROTE ", OUT, " size=", img.get_width(), "x", img.get_height())
	get_tree().quit(0)
