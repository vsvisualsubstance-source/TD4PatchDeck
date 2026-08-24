uniform vec3 u_transform, u_rotate;
uniform vec2 u_thresh;
uniform float u_period, u_amp, u_offset;

vec2 rotate(vec2 p, float theta) {
	
	theta = radians(theta);
    float s = sin(theta);
    float c = cos(theta);
    mat2 m = mat2(c, s, -s, c);
    return m * p;
}

out vec4 fragColor;
void main()
{
	vec3 p = texture(sTD2DInputs[0], vUV.st).xyz;
	p.xy = rotate(p.xy, u_rotate.x);
	p.yz = rotate(p.yz, u_rotate.y);
	p.zx = rotate(p.zx, u_rotate.z);
	
	p *= 10.0/u_period;
	p -= u_transform;
	
	
	float gyroid = dot(sin(p), cos(p.zxy));
	
	gyroid *= u_amp;
	gyroid += u_offset;
	
	gyroid = smoothstep(u_thresh.x, u_thresh.y, gyroid);
	
	vec4 color = vec4(gyroid);
	fragColor = TDOutputSwizzle(color);
}
