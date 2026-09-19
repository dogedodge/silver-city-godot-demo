extends Node2D
## Tiles the grass texture across the play area.

@export var texture: Texture2D
@export var area_size := Vector2(5120, 2880)

func _ready() -> void:
	queue_redraw()


func _draw() -> void:
	if texture == null:
		return
	var tw := float(texture.get_width())
	var th := float(texture.get_height())
	if tw <= 0.0 or th <= 0.0:
		return
	var x := 0.0
	while x < area_size.x:
		var y := 0.0
		while y < area_size.y:
			draw_texture_rect(
				texture,
				Rect2(x, y, minf(tw, area_size.x - x), minf(th, area_size.y - y)),
				false
			)
			y += th
		x += tw
