
// Example Pixel Shader

// uniform float exampleUniform;

out vec4 fragColor;
void main()
{
	vec2 uv = vUV.xy * 2.0 - 1.0;
	
	float r = exp(-abs(uv.y) * 8.0) * 4.0;
	float g = exp(-abs(uv.y) * 7.0) * 4.0;
	float b = exp(-abs(uv.y) * 6.0) * 4.0;
	// vec4 color = texture(sTD2DInputs[0], vUV.st);
	vec4 color = vec4(r,g,b,1.0);
	fragColor = TDOutputSwizzle(color);
}
