uniform float uRandom;
uniform float uNumPoints;
uniform vec3 uLinePtA;
uniform vec3 uLinePtB;

#define PI 3.141592653589793;

vec3 createNormal(in vec3 normLine)
{
	vec3 normVec = vec3(1.0,0.0,0.0);
	float angle = acos(dot(normLine, normVec));
	vec3 axis = cross(normLine, normVec);

	float c = cos(angle);
	float s = sin(angle);
	float t = 1-c;

	// rotate around vec3(0,0,1)
	mat4 rotMat;
	rotMat[0] = vec4(c,-s,0,0);
	rotMat[1] = vec4(s,c,0,0);
	rotMat[2] = vec4(0,0,c+t,0);
	rotMat[3] = vec4(0.0,0.0,0.0,1.0);

	vec4 newPer = vec4(0,1,0,1) * rotMat;
	return newPer.xyz;
}

void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int	pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = texture(sTD2DInputs[0], vUV);
	rnd = (rnd + 1.0) / 2.0;
	vec3 lineVec = uLinePtB - uLinePtA;
	point = uLinePtA + lineVec * rnd.x;

	vec3 normLine = lineVec / length(lineVec);
	vec3 newPer = createNormal(normLine);

	gPoint.pos = point;
	gPoint.norm = newPer.xyz;
}