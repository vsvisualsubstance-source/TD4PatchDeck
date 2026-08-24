uniform float u_vorticity,u_time_step,u_pressure,u_decay,u_smagorinsky,u_viscosity;

vec2 pixel_size=uTD2DInfos[0].res.xy;
vec2 pixel_hori=vec2(pixel_size.x,0.);
vec2 pixel_verti=vec2(0.,pixel_size.y);

float curl(vec2 uv)
{
    float r=texture(sTD2DInputs[0],uv+pixel_hori).y;
    float l=texture(sTD2DInputs[0],uv-pixel_hori).y;
    float t=texture(sTD2DInputs[0],uv+pixel_verti).x;
    float b=texture(sTD2DInputs[0],uv-pixel_verti).x;
    
    return(l-r-b+t)*.5;
}

vec2 curl_slope(vec2 uv)
{
    float curl_r=curl(uv+pixel_hori);
    float curl_l=curl(uv-pixel_hori);
    float curl_t=curl(uv+pixel_verti);
    float curl_b=curl(uv-pixel_verti);
    
    return vec2(abs(curl_r)-abs(curl_l),abs(curl_t)-abs(curl_b))*.5;// abs becuase sign gets added at vorticity stage
}

// https://www.shadertoy.com/view/cdGfzz
vec2 safe_norm(vec2 v)
{
    v=normalize(v);
    return any(isinf(v))||any(isnan(v))?vec2(0):v;
}

float divergence(vec2 uv)
{
    float left=texture(sTD2DInputs[0],uv-pixel_hori).x;
    float right=texture(sTD2DInputs[0],uv+pixel_hori).x;
    float top=texture(sTD2DInputs[0],uv+pixel_verti).y;
    float bottom=texture(sTD2DInputs[0],uv-pixel_verti).y;
    
    return((right-left)+(top-bottom))*.5;
}

float pressure(vec2 uv)
{
    float left=texture(sTD2DInputs[0],uv-pixel_hori).w;
    float right=texture(sTD2DInputs[0],uv+pixel_hori).w;
    float top=texture(sTD2DInputs[0],uv+pixel_verti).w;
    float bottom=texture(sTD2DInputs[0],uv-pixel_verti).w;
    
    float pressure=(left+right+top+bottom-divergence(uv))*.25;
    
    return pressure;
}

vec2 pressure_grad(vec2 uv)
{
    
    float p_left=pressure(uv-pixel_hori);
    float p_right=pressure(uv+pixel_hori);
    float p_top=pressure(uv+pixel_verti);
    float p_bottom=pressure(uv-pixel_verti);
    
    vec2 grad=vec2(p_right-p_left,p_top-p_bottom);
    return grad;
    }
    
    out vec4 fragColor;
    void main()
    {
        vec2 uv=vUV.xy;
        vec2 velocity=texture(sTD2DInputs[0],uv).xy;
        
        // vorticity and curl
        float curl_val=curl(uv);
        vec2 curl_grad=curl_slope(uv);
        curl_grad=safe_norm(curl_grad);
        
        vec2 force=vec2(-curl_grad.y,curl_grad.x);
        force*=u_vorticity*(curl_val);
        
        force*=u_time_step;
        velocity+=force;
        // pressure
        vec2 adv=velocity*pixel_size*u_time_step;
        float clear_press=pressure(uv)*clamp(1.-u_pressure*u_time_step,0.,1.);
        
        velocity.xy-=pressure_grad(uv);
        //------------------//
        
        vec2 ul=texture(sTD2DInputs[0],uv-pixel_hori).xy;
        vec2 ur=texture(sTD2DInputs[0],uv+pixel_hori).xy;
        vec2 ub=texture(sTD2DInputs[0],uv-pixel_verti).xy;
        vec2 ut=texture(sTD2DInputs[0],uv+pixel_verti).xy;
        
        // central‐difference gradients
        float du_dx=(ur.x-ul.x)*.5;
        float du_dy=(ut.x-ub.x)*.5;
        float dv_dx=(ur.y-ul.y)*.5;
        float dv_dy=(ut.y-ub.y)*.5;
        
        // strain components
        float Sxx=du_dx;
        float Syy=dv_dy;
        float Sxy=.5*(du_dy+dv_dx);
        
        float Cs=u_smagorinsky;
        float delta=pixel_size.y;
        float magS=sqrt(2.*(Sxx*Sxx+2.*Sxy*Sxy+Syy*Syy));
        float nu_t=Cs*Cs*delta*delta*magS;
        
        vec2 lap=
        (ul+ur+ub+ut-4.*velocity)/(delta*delta);
        
        // molecular viscosity (if any)
        float nu=u_viscosity*u_time_step*pixel_size.y;
        
        // add eddy-diffusion
        velocity+=(nu+nu_t)*u_time_step*lap;
        
        velocity*=clamp(1.-u_decay*u_time_step,0.,1.);
        
        vec4 color=vec4(velocity,0.,clear_press);
        fragColor=TDOutputSwizzle(color);
    }
    