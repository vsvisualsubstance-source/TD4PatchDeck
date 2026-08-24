uniform float u_inp_vel;
out vec4 fragColor;

void main()
{
    vec2 input_vel = texture(sTD2DInputs[0], vUV.st).xy * u_inp_vel;
    vec2 fb_vel = texture(sTD2DInputs[1], vUV.st).xy;
    float bounds = 1.0-(texture(sTD2DInputs[2], vUV.st).x);
	vec2 vel = (input_vel * bounds) + fb_vel;
    
    
     float alpha = texture(sTD2DInputs[1], vUV.st).w;
	vec4 color = vec4(vel, 0.0, alpha);
    fragColor = TDOutputSwizzle(color);
}