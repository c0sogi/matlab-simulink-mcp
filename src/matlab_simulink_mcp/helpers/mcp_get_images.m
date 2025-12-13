function cwds = mcp_get_images()
    figs = findall(0, 'type', 'figure');  
    num = numel(figs);
    if num == 0 
        cwds = {};     
    else
        cwds = cell(1, num);
        for k = 1:num
            % Write to a unique temp file to avoid cluttering `pwd` and to reduce
            % failures when the current working directory is not writable.
            filename = [tempname '.png'];
            saveas(figs(k), filename);
            cwds{k} = filename;
        end 
    end
end
