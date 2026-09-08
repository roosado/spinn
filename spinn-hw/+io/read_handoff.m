function data = read_handoff(filename)
%READ_HANDOFF Load a spinn design->as-built handoff HDF5 file into a struct.
%   DATA = IO.READ_HANDOFF(FILENAME) reads the one-directional handoff written by
%   the Python side (spinn/export.py) and returns a struct.
%
%   This function only reads. It never writes back into the Python pipeline --
%   the design/as-built boundary is one-directional by design (CLAUDE.md).
%
%   The file's schema version is checked below; an unknown version is an error so
%   the MATLAB side never silently misreads a file written by a different
%   contract. The version restarts at 0.1.0: this is spinn's schema, not a
%   continuation of photonn's, and reusing their numbering would imply a
%   compatibility that does not exist.
%
%   Note on array order: MATLAB's h5read returns datasets with dimensions
%   reversed relative to the Python (row-major) writer. A Python f8[nRows, nCols]
%   comes back here as nCols-by-nRows, so weights are transposed on the way in.
%   That is the one place in this file where getting it wrong yields a valid
%   array rather than an error -- a transposed conductance matrix is still a
%   conductance matrix, it runs, and it returns a wrong number. The zero-error
%   accuracy cross-check against the handoff's own test_acc is what catches it.

    SUPPORTED_SCHEMAS = "0.1.0";

    if ~isfile(filename)
        error("io:read_handoff:fileNotFound", "File not found: %s", filename);
    end

    schema = string(h5readatt(filename, "/", "schema_version"));
    if ~ismember(schema, SUPPORTED_SCHEMAS)
        error("io:read_handoff:schemaMismatch", ...
            "Schema version mismatch: file '%s', supported [%s].", ...
            schema, strjoin(SUPPORTED_SCHEMAS, ", "));
    end

    data = struct();
    data.schema_version = schema;
    data.description = string(h5readatt(filename, "/", "description"));

    modelType = string(h5readatt(filename, "/parameters", "model_type"));
    if modelType ~= "crossbar"
        error("io:read_handoff:badModelType", ...
            "Unknown model_type '%s'; this reader knows 'crossbar'.", modelType);
    end
    data.model_type = modelType;

    % -- geometry --------------------------------------------------------
    data.geometry.n_rows            = double(h5readatt(filename, "/geometry", "n_rows"));
    data.geometry.n_cols            = double(h5readatt(filename, "/geometry", "n_cols"));
    data.geometry.devices_per_weight = double(h5readatt(filename, "/geometry", "devices_per_weight"));

    % -- operating point -------------------------------------------------
    % Every one of these is required, and absence is an error rather than a
    % default. That is inherited from photonn and it is the most valuable habit on
    % this seam, because the failure it prevents does not look like a failure:
    % rename readout_gain and MATLAB quietly substitutes 1.0, rescaling every
    % logit into a published tolerance number with nothing to point at.
    %
    % Here the same trap is set by signed_scheme_code. Default it to 0 and an
    % offset array is reconstructed as a differential one: every conductance is
    % wrong, nothing errors, and the accuracy is merely poor rather than absent.
    %
    % This set mirrors spinn.export.OPERATING_POINT, which the writer enforces, so
    % a file reaching here without one of these did not come from write_handoff
    % and should not be read as though it had.
    op = "/operating_point";
    required = ["g_min_s", "g_max_s", "read_voltage_v", "readout_gain", ...
                "signed_scheme_code"];
    for name = required
        data.operating_point.(name) = requiredAttr(filename, op, name, modelType);
    end

    switch data.operating_point.signed_scheme_code
        case 0
            data.scheme = "differential";
        case 1
            data.scheme = "offset";
        otherwise
            error("io:read_handoff:badScheme", ...
                "signed_scheme_code must be 0 (differential) or 1 (offset); got %g.", ...
                data.operating_point.signed_scheme_code);
    end

    expectedDevices = 2 - (data.scheme == "offset");
    if data.geometry.devices_per_weight ~= expectedDevices
        error("io:read_handoff:schemeMismatch", ...
            "devices_per_weight=%g disagrees with scheme '%s' (%d per weight).", ...
            data.geometry.devices_per_weight, data.scheme, expectedDevices);
    end

    % -- parameters ------------------------------------------------------
    % Transposed: see the note in the header. Python writes [nRows, nCols].
    weights = h5read(filename, "/parameters/weights").';
    if ~isequal(size(weights), [data.geometry.n_rows, data.geometry.n_cols])
        error("io:read_handoff:badWeightShape", ...
            "weights are %s after transpose; geometry says %d-by-%d.", ...
            mat2str(size(weights)), data.geometry.n_rows, data.geometry.n_cols);
    end
    data.parameters.weights = weights;

    % -- frozen test set --------------------------------------------------
    % Python writes f4[n, g, g]; h5read reverses to g-by-g-by-n. Permuting the
    % first two axes undoes the row/column swap within each image, and the images
    % are flattened by model.crossbar in the same order Python flattens them.
    images = h5read(filename, "/test_set/images");
    data.test_set.images = permute(double(images), [2 1 3]);
    data.test_set.labels = double(h5read(filename, "/test_set/labels"));

    % The ideal accuracy the design side measured. Carried as a real attribute so
    % the as-built model can cross-check itself at zero error rather than trusting
    % that it reconstructed the array correctly.
    try
        data.test_acc = double(h5readatt(filename, "/", "test_acc"));
    catch
        data.test_acc = NaN;
    end
end


function v = requiredAttr(filename, group, name, modelType)
%REQUIREDATTR Read an HDF5 attribute, erroring with a usable message if absent.
%   Deliberately has no default. A default here is indistinguishable from a
%   correct value downstream, which is how a renamed field used to become a
%   plausible wrong answer instead of a stack trace.
    try
        v = double(h5readatt(filename, group, name));
    catch
        error("io:read_handoff:missingOperatingPoint", ...
            ['Handoff is missing %s/%s, required for model_type=''%s''.\n' ...
             'The writer enforces spinn.export.OPERATING_POINT, so this file ' ...
             'did not come from write_handoff. Re-export it rather than ' ...
             'supplying a default here -- a default is indistinguishable from ' ...
             'a correct value everywhere downstream.'], group, name, modelType);
    end
end
