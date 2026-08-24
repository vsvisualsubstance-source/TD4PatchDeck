uniform vec2 uRes;

out vec4 fragColor;
void main()
{
	//vec2 onePixel = vec2(1.0, 1.0) / uRes;

	vec2 cUV = vec2(vUV.s, vUV.t);
	vec4 color = texture(sTD2DInputs[0], cUV);

	vec2 fUV = vec2(vUV.s, vUV.t * (vUV.t / (0.1 * (color.r + color.g + color.b))));
	vec4 feedback = texture(sTD2DInputs[1], fUV);
	vec4 feedbackFull = texture(sTD2DInputs[1], vUV.st);

	vec4 matte = feedback / color;
	vec4 comp = vec4(matte.a) * (color + feedbackFull);

	comp.a = matte.a;

	fragColor = TDOutputSwizzle(comp);
}