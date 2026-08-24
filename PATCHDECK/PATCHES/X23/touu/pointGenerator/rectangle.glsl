uniform float uRandom;
uniform float uNumPoints;
uniform int uOrientation;
uniform vec3 uSize;

void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int	pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = texture(sTD2DInputs[0], vUV);
	int axis = int(mod(uOrientation+2,3));
	rnd[axis] = 0.0;
	vec3 norm = vec3(0.0);
	norm[axis] = 1.0;
	vec3 size = uSize;
	if (uOrientation == 1)
	{
		size = vec3(0.0, size.x, size.y);
	} 
	else if (uOrientation == 2)
	{
		size = vec3(size.x, 0.0, size.y);
	}
	point = point + (rnd.xyz * size * uRandom);
	gPoint.pos = point;
	gPoint.norm = norm;
}