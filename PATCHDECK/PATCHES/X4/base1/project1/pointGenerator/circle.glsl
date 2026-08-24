uniform float uRandom;
uniform float uNumPoints;
uniform vec2 uRadius;
uniform int uOrientation;

void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int	pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = texture(sTD2DInputs[0], vUV);
	int axis = int(mod(uOrientation+2,3));
	rnd[axis] = 0.0; 
	rnd.xyz = rnd.xyz / length( rnd.xyz );
	vec3 radius = vec3(uRadius, 0.0);
	if (uOrientation == 1)
	{
		radius = vec3(0.0, uRadius);
	}
	else if (uOrientation == 2)
	{
		radius = vec3(uRadius.x, 0.0, uRadius.y);
	}
	point = (rnd.xyz * radius * uRandom);
	gPoint.pos = point;
	gPoint.norm = point;
}