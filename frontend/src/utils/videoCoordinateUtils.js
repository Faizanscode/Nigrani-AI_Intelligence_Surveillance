/**
 * videoCoordinateUtils.js
 * 
 * Provides coordinate transformations between raw browser/display coordinates 
 * and normalized source video coordinates [0.0 - 1.0], specifically accounting 
 * for `object-fit: contain` letterboxing/pillarboxing.
 */

/**
 * Calculates the exact rendered rectangle of an image within its container
 * when styled with `object-fit: contain`.
 * 
 * @param {number} containerWidth - The width of the HTML container (e.g., canvas or div)
 * @param {number} containerHeight - The height of the HTML container
 * @param {number} naturalWidth - The source/intrinsic width of the image
 * @param {number} naturalHeight - The source/intrinsic height of the image
 * @returns {object} { x, y, width, height }
 */
export function getRenderedRect(containerWidth, containerHeight, naturalWidth, naturalHeight) {
    if (!naturalWidth || !naturalHeight || !containerWidth || !containerHeight) {
        // Fallback if dimensions are not available yet
        return { x: 0, y: 0, width: containerWidth, height: containerHeight };
    }

    const containerRatio = containerWidth / containerHeight;
    const imageRatio = naturalWidth / naturalHeight;

    let renderWidth, renderHeight;

    if (imageRatio > containerRatio) {
        // Image is wider than container (letterbox on top and bottom)
        renderWidth = containerWidth;
        renderHeight = containerWidth / imageRatio;
    } else {
        // Image is taller than container (pillarbox on left and right)
        renderHeight = containerHeight;
        renderWidth = containerHeight * imageRatio;
    }

    // Centered by default with object-fit: contain
    const x = (containerWidth - renderWidth) / 2;
    const y = (containerHeight - renderHeight) / 2;

    return { x, y, width: renderWidth, height: renderHeight };
}

/**
 * Converts a raw mouse coordinate (relative to the container) to a normalized [0.0, 1.0] 
 * coordinate relative strictly to the actual rendered video content.
 * 
 * @param {number} clientX - Mouse X relative to container (e.g., from e.clientX - rect.left)
 * @param {number} clientY - Mouse Y relative to container
 * @param {object} containerRect - { width, height } of the container
 * @param {number} naturalWidth - Source width of the image
 * @param {number} naturalHeight - Source height of the image
 * @returns {number[]} [nx, ny] - Normalized coordinates
 */
export function displayToNormalized(clientX, clientY, containerRect, naturalWidth, naturalHeight) {
    const renderRect = getRenderedRect(
        containerRect.width, 
        containerRect.height, 
        naturalWidth, 
        naturalHeight
    );

    // Calculate position relative to the rendered image bounds
    const xInImage = clientX - renderRect.x;
    const yInImage = clientY - renderRect.y;

    // Normalize and clamp to [0, 1] to prevent clicking outside the video frame
    const nx = Math.max(0, Math.min(1, xInImage / renderRect.width));
    const ny = Math.max(0, Math.min(1, yInImage / renderRect.height));

    return [parseFloat(nx.toFixed(4)), parseFloat(ny.toFixed(4))];
}

/**
 * Converts a normalized [0.0, 1.0] coordinate (relative to the source video)
 * back to a display coordinate (relative to the container) for canvas drawing.
 * 
 * @param {number} nx - Normalized X
 * @param {number} ny - Normalized Y
 * @param {number} containerWidth - The width of the HTML container
 * @param {number} containerHeight - The height of the HTML container
 * @param {number} naturalWidth - Source width of the image
 * @param {number} naturalHeight - Source height of the image
 * @returns {number[]} [displayX, displayY]
 */
export function normalizedToDisplay(nx, ny, containerWidth, containerHeight, naturalWidth, naturalHeight) {
    const renderRect = getRenderedRect(
        containerWidth, 
        containerHeight, 
        naturalWidth, 
        naturalHeight
    );

    const displayX = renderRect.x + (nx * renderRect.width);
    const displayY = renderRect.y + (ny * renderRect.height);

    return [displayX, displayY];
}
