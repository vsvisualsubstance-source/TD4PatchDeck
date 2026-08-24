uniform float u_delta_time, u_passes;


layout(location = 0) out vec4 fragColor;
layout(location = 1) out vec4 fragColor2;

void main()
{
	vec3 vel = texture(sTD2DInputs[0], vUV.st).xyw;
	//vel *= uTD2DInfos[0].res.xy * u_delta_time * u_passes;
	vec4 disp_vel = vec4(vel.xy * uTD2DInfos[0].res.xy * u_delta_time * u_passes, 0.0,1.0);
	vec4 col_vel =  vec4(vel * u_delta_time,1.0);
	fragColor = TDOutputSwizzle(disp_vel);
	fragColor2 = TDOutputSwizzle(col_vel);
	vec4 color = vec4(1.0);

}
