function cwd = snapshot_system(system_path, main_system, open)

load_system(main_system)

if open
    open_system(system_path);
end

dpi = '150'; 
path = "-s" + system_path;
quality = "-r" + dpi;
file = "snapshot.png";

print(path, "-dpng", quality, file);

cwd = fullfile(pwd, 'snapshot.png');

end