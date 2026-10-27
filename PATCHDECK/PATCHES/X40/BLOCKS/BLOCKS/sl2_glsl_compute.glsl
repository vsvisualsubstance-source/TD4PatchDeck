// Example Compute Shader

// uniform float exampleUniform;

layout (local_size_x = 8, local_size_y = 4) in;
void main()
{
	// This code is running 1:1 per pixel, so early-exit
	// if this thread overhangs the edge of the output
	if (any(greaterThanEqual(ivec2(gl_GlobalInvocationID.xy), ivec2(uTDOutputInfo.res.zw))))
		return;

	vec4 color;
	//color = texelFetch(sTD2DInputs[0], ivec2(gl_GlobalInvocationID.xy), 0);
	color = vec4(1.0);
	// We need to use TDImageStoreOutput() so that 8-bit textures that are sRGB
	// encoded can be written to correctly from incoming linear values.
	// imageStore() does not do this automatically, while pixel shader outputs do.
	TDImageStoreOutput(0, gl_GlobalInvocationID, color);
}
