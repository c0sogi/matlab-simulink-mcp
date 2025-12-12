function cwd = mcp_snapshot_system(system_path, main_system, open)
%SNAPSHOT_SYSTEM Create a PNG snapshot of a Simulink system/subsystem.
% Returns an absolute file path to the created PNG.

    try
        load_system(main_system);
    catch
        % fall back to loading a .slx if needed
        try
            load_system([main_system, '.slx']);
        catch
        end
    end

    if open
        try
            open_system(system_path);
        catch
        end
    end

    % Unique output file to avoid collisions across calls
    safeName = regexprep(char(system_path), '[^a-zA-Z0-9]', '_');
    fname = ['snapshot_', safeName, '_', char(java.util.UUID.randomUUID), '.png'];
    file = fullfile(tempdir, fname);

    dpi = '150';
    pathArg = "-s" + string(system_path);
    quality = "-r" + dpi;

    print(pathArg, "-dpng", quality, file);
    cwd = file;
end