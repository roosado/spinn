function V = encode(handoff, images)
%ENCODE Flatten images to row voltages, scaled to the read voltage.
%   V = MODEL.ENCODE(HANDOFF, IMAGES) takes IMAGES as g-by-g-by-n (the
%   orientation io.read_handoff returns) and gives V as n-by-nRows.
%
%   Per-sample L-infinity normalisation: the physical constraint is a maximum
%   read voltage, so the largest pixel in each sample sits at read_voltage_v.
%
%   The flatten is row-major, matching how Python flattens the same image. MATLAB
%   is column-major, so the permute below is not cosmetic: without it every image
%   is transposed, the array still runs, and the accuracy is merely poor.
    nRows = handoff.geometry.n_rows;
    flat = reshape(permute(images, [2 1 3]), nRows, []).';   % n-by-nRows

    peak = max(abs(flat), [], 2);
    peak(peak == 0) = 1;
    V = handoff.operating_point.read_voltage_v * (flat ./ peak);
end
