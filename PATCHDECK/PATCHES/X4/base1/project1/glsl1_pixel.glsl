uniform float u_delta_time, u_life_time;

out vec4 fragColor;
void main()
{
	vec2 p = texture(sTD2DInputs[0], vUV.st).xy;
	vec2 vel = texture(sTD2DInputs[1], p).xy;
	float life = texture(sTD2DInputs[0],vUV.xy).a;
	vec2 init_p = texture(sTD2DInputs[2], vUV.xy).xy;
	
	life += (1.0/u_life_time) * u_delta_time;
	
	if(life > 1.0)
		{
			life = 0.0;
			p = init_p;
		}
	
	
	p += vel * 0.8;
	vec4 color = vec4(p, 0.0, life);
	fragColor = TDOutputSwizzle(color);
}
