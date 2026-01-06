#!/usr/bin/env fish

set K8S_VERSION "1.35.0"
set CNPG_VERSION "1.28.0"

mkdir "v$CNPG_VERSION" && cd "v$CNPG_VERSION"

curl http://localhost:8080/openapi/v3/apis/postgresql.cnpg.io/v1 | jq '.components.schemas' > openapi_response.json
sed -i $(string join '' 's/"\$ref": "\#\/components\/schemas\/io.k8s/"\$ref": "https:\/\/raw.githubusercontent.com\/yannh\/kubernetes-json-schema\/master\/v' $K8S_VERSION '\/_definitions.json\#\/definitions\/io.k8s/g') openapi_response.json

set keys $(string split "," $(cat openapi_response.json | jq -r 'keys | join(",")'))

for key in $keys
	if not string match 'io.cnpg.postgresql*' $key
		continue
	end
	cat openapi_response.json | jq ".\"$key\"" > $key.json
end

rm openapi_response.json

cd ..
