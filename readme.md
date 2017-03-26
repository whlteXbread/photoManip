# Photo Manipulation Tools

## average_months.py
The idea behind this script is to download all the photos from a Flickr set specified by its set ID, organize them by month taken, and then generate one average image (or long exposure simulation) for each month. It leverages `avg_phoots.py` to do the photo manipulation.

Usage:
```
    ./average_months.py [flickr_set_id]
```

## avg_phoots.py
This script will generate an average image (or long exposure simulation) using all the images in a specified folder. 

Usage: 
```
    ./avg_phoots.py [folder] [combination_method] [output_file_name]
```
`folder` is any folder you have permission to read that contains `.jpg` files.
`combination_method` is either `crop` or `pad`. `crop` means that all images are cropped into square images with dimensions equal to the smallest dimension found in all the images in the folder. `pad` means that all images are padded into square images with dimensions equal to the largest dimension found in all the images in the folder.
`output_file_name` is the filename that the average image will be written to.