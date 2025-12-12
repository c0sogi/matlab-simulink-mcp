function format_system()
%function result = format_system(system_path, main_system, arrange)
%load_system(main_system)

%if arrange
%    Simulink.BlockDiagram.arrangeSystem(system_path);
%end 

systems = find_system('type','block_diagram');

for i = 1:numel(systems)
    sys = systems{i};
    hLines = find_system(sys, 'FindAll', 'on', 'Type', 'line', 'Connected', 'off');
    delete_line(hLines);
end

%hLines = find_system(system_path, 'SearchDepth', 1, 'FindAll', 'on', 'Type', 'Line', 'Connected', 'off');
%delete_line(hLines);
%result = "Success";


