extends Node
## Snapshot the playable skeletal run scene, then quit.
##   godot --path . res://tests/dump_xiaolv_game.tscn

const OUT := "/tmp/xiaolv_game.png"


func _ready() -> void:
	var packed: PackedScene = load("res://scenes/xiaolv_skel_run.tscn")
	var scene := packed.instantiate()
	add_child(scene)
	await get_tree().create_timer(0.45).timeout
	var img := get_viewport().get_texture().get_image()
	img.save_png(OUT)
	print("DUMP GAME WROTE ", OUT)
	get_tree().quit(0)
