<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">

  <title>EMU-1.0 Gallery</title>
  <meta name="description" content="The EMU-1.0 Paint Gallery">
  <meta name="author" content="Quphoria">

  <link rel="stylesheet" href="stylesheet.css">

</head>

<body>
  


<?php
$image = end(explode("/",$_SERVER['REQUEST_URI']));
$path = 'images';
if($image === "") {
    echo "<h1> EMU-1.0 PAINT GALLERY </h1>";
    echo "<a style='font-size:.8em' href='paint.zip'>[Download the ROM]</a></br></br>";
    $files = array();
    if ($handle = opendir('./' . $path)) {
        while (false !== ($file = readdir($handle))) {
            if ($file != "." && $file != "..") {
            $realfile = $path . "/" . $file;
            $files[filemtime('./' . $realfile) . $file] = $realfile;
            }
        }
        closedir($handle);

        // sort
        krsort($files);
        // find the last modification
        $reallyLastModified = end($files);

        foreach($files as $file) {
            $lastModified = date('F d Y, H:i:s',filemtime($file));
            if(strlen($file)-strpos($file,".png")== 4){
            if ($file == $reallyLastModified) {
                // do stuff for the real last modified file
            }
            $imagename = explode(".", end(explode("/", $file)))[0];
            echo "<a href='" . $imagename . "'><img class='small' src='" . $file . "'/></a>&nbsp;";
            }
        }
    }
} else {
    echo "<a href='/'>Back to gallery</a>";
    $image = strtolower($image);
    if(preg_match("/^[a-zA-Z0-9]+$/", $image) == 1) {
        $file = $path . "/" . $image . ".png";
        if (file_exists("./" . $file)) {
            echo "<div class='bigdiv'><img class='big' src='" . $file . "'/></div>&nbsp;";
        } else {
            echo "<h3>Image not found.</h3>";
        }
    } else {
        echo "<h3>Image urls may only contain A-Z, a-z, 0-9</h3>";
    }
}
?>

<!-- <script src="js/scripts.js"></script> -->
</body>
</html>