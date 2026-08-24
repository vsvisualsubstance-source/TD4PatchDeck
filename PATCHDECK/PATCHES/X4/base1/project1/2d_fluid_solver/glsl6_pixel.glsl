uniform float u_time_step;
uniform float u_damping;
uniform bool u_reflective;

vec2 pixel_size=uTD2DInfos[0].res.xy;

vec2 safe_norm(vec2 v)
{
	v=normalize(v);return any(isinf(v))||any(isnan(v))?vec2(0):v;
}

vec2 boundary_gradient(vec2 uv){
	vec2 c_diff=vec2(dFdx(texture(sTD2DInputs[1],uv).x),
	dFdy(texture(sTD2DInputs[1],uv).x));
	
	return c_diff;
}

out vec4 fragColor;
void main()
{
//advection
    vec2 uv=vUV.xy;
    
    vec2 k1=texture(sTD2DInputs[0],(uv)).xy;
    
    vec2 pos2=uv-.5*u_time_step*k1*pixel_size;
    vec2 k2=texture(sTD2DInputs[0],(pos2)).xy;
    
    vec2 pos3=uv-.5*u_time_step*k2*pixel_size;
    vec2 k3=texture(sTD2DInputs[0],(pos3)).xy;
    
    vec2 pos4=uv-u_time_step*k3*pixel_size;
    vec2 k4=texture(sTD2DInputs[0],(pos4)).xy;
    
    vec2 final_p=uv-(u_time_step/6.)*(k1+2.*k2+2.*k3+k4)*pixel_size;
    
    vec2 vel=texture(sTD2DInputs[0],final_p).xy;
 

//boundary
	float bounds = texture(sTD2DInputs[1],uv).x;
    
    if(u_reflective==true)
	{
		vec2 n=safe_norm(boundary_gradient(uv));
		//float d = dot(vel, n);
		vec2 r_vel=reflect(vel,n);
		r_vel*=u_damping;
		vel=mix(vel,vec2(r_vel),bounds);
	}
	else
	{
		vel=mix(vel,vec2(0.),bounds);
	}
    
    
    
    
    float alpha=texture(sTD2DInputs[0],vUV.xy).w;//passing the pressure through
    vec4 color=vec4(vel,0.,alpha);
    fragColor=TDOutputSwizzle(color);
}