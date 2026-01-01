#!/usr/bin/env fish

set TALOS_VERSION v1.12.0
set ARCH amd64
set EXTENSIONS "$(crane export ghcr.io/siderolabs/extensions:$TALOS_VERSION | tar x -O image-digests)"

cd extensions

git fetch --all
git reset --hard origin/main

cd network

set TAILSCALE_RELEASE (
	curl -sL \
        	-H "Accept: application/vnd.github+json" \
        	-H "X-GitHub-Api-Version: 2022-11-28" \
        	https://api.github.com/repos/tailscale/tailscale/releases 
)

set TAILSCALE_DOWNLOAD_FILE_NAME tailscale_sha.tar.gz

set TAILSCALE (
	echo $TAILSCALE_RELEASE |
	jq -r .[0].name | 
	string match -gr 'v(.*)' --
)

curl -o $TAILSCALE_DOWNLOAD_FILE_NAME -L "https://github.com/tailscale/tailscale/archive/refs/tags/v$TAILSCALE.tar.gz"

set TAILSCALE_SHA256 (string split ' ' (sha256sum $TAILSCALE_DOWNLOAD_FILE_NAME))[1]
set TAILSCALE_SHA512 (string split ' ' (sha512sum $TAILSCALE_DOWNLOAD_FILE_NAME))[1]

function change_key -a key value
	sed -i -r -e "s/($key:) (.*)/\1 $value/g" vars.yaml
end

change_key "TAILSCALE_VERSION" $TAILSCALE
change_key "TAILSCALE_SHA256" $TAILSCALE_SHA256
change_key "TAILSCALE_SHA512" $TAILSCALE_SHA512

rm $TAILSCALE_DOWNLOAD_FILE_NAME
cd ..

make tailscale PLATFORM=linux/amd64
docker tag ghcr.io/siderolabs/tailscale:$TAILSCALE git.prettysunflower.moe/prettysunflower/talos-tailscale:$TAILSCALE
docker push git.prettysunflower.moe/prettysunflower/talos-tailscale:$TAILSCALE

cd ..

docker run --rm -t -v /dev:/dev --privileged \
    -v "$PWD/_out:/out" "ghcr.io/siderolabs/imager:$TALOS_VERSION" installer --arch "$ARCH" \
    --system-extension-image (echo $EXTENSIONS | grep "/iscsi-tools") \
    --system-extension-image (echo $EXTENSIONS | grep "/qemu-guest-agent") \
    --system-extension-image (echo $EXTENSIONS | grep "/util-linux-tools") \
    --system-extension-image git.prettysunflower.moe/prettysunflower/talos-tailscale:$TAILSCALE

set IMAGE_NAME git.prettysunflower.moe/prettysunflower/talos:$TALOS_VERSION-tailscale-$TAILSCALE

docker load -i ./_out/installer-$ARCH.tar
docker tag ghcr.io/siderolabs/installer-base:$TALOS_VERSION $IMAGE_NAME
docker push $IMAGE_NAME
