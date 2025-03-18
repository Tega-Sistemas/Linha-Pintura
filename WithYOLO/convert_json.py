import json
import os

def convert_json_to_yolo(json_file, output_dir, class_id=0):
    """
    Converte anotações do MakeSense.ai (JSON) para o formato YOLO (.txt).
    :param json_file: Caminho do arquivo JSON exportado do MakeSense.
    :param output_dir: Diretório onde os arquivos YOLO serão salvos.
    :param class_id: ID da classe para as chapas de madeira (0 por padrão).
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for image in data["images"]:
        image_name = image["file_name"]  # Correção aqui
        width = image["width"]
        height = image["height"]
        annotations = [ann for ann in data["annotations"] if ann["image_id"] == image["id"]]
        
        txt_filename = os.path.join(output_dir, os.path.splitext(image_name)[0] + ".txt")
        with open(txt_filename, "w") as txt_file:
            for ann in annotations:
                points = ann["segmentation"][0]  # Pega os pontos do polígono
                
                # Converter polígono para retângulo delimitador (bounding box)
                x_coords = points[0::2]
                y_coords = points[1::2]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                x_center = (x_min + x_max) / 2 / width
                y_center = (y_min + y_max) / 2 / height
                bbox_width = (x_max - x_min) / width
                bbox_height = (y_max - y_min) / height
                
                txt_file.write(f"{class_id} {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}\n")
    
    print(f"Conversão concluída! Arquivos salvos em {output_dir}")
    
if __name__ == "__main__":
    json_path = "C:\\Users\\NTB_ACER_DEV\\Desktop\\Testar\\labels_my-project-name_2025-01-31-05-59-45.json"
    output_dir = "C:\\Users\\NTB_ACER_DEV\\Desktop\\Testar\\output_yolo"

    convert_json_to_yolo(json_path, output_dir)

