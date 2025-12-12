function cwds = get_images()
    figs = findall(0, 'type', 'figure');  
    num = numel(figs);
    if num == 0 
        cwds = {};     
    else
        cwds = cell(1, num);
        for k = 1:num
            filename = sprintf('temp_plot_%d.png', k);
            saveas(figs(k), filename);
            cwds{k} = fullfile(pwd, filename);
        end 
    end
end
