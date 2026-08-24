const vec3 W = vec3(0.2989, 0.5870, 0.1140);

float luminance(vec3 rgb)
{
	return dot(rgb, W);
}

uniform float uInputLevel;
uniform float uBloomIntensity;
uniform float uGlowIntensity;
uniform vec3 uGlowColor;
uniform float uRampIntensity;


layout(location = 0) out vec4 fragColor;
layout(location = 1) out vec4 bloomColor;
void main()
{

	vec4 inputTexture = texture(sTD2DInputs[0], vUV.st);
	vec3 bloom = texture(sTD2DInputs[1], vUV.st).rgb;


	float luma = luminance(bloom);

	bloom *= uBloomIntensity;

	if (uGlowIntensity > 0.0)
	{
		bloom += uGlowColor * luma * uGlowIntensity;
	}

	if (uRampIntensity > 0.0)
	{
		bloom += texture(sTD2DInputs[2], vec2(luma, 0.5)).rgb * uRampIntensity;
	}



	fragColor = TDOutputSwizzle(inputTexture * uInputLevel + vec4(bloom, luma));
	bloomColor = TDOutputSwizzle(vec4(bloom, luma));

}
