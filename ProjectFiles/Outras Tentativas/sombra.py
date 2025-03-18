import tkinter as tk
from tkinter import filedialog
import csv

class CompressedCSVView:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualização Sombra Esteira")
        self.root.geometry("1000x1000")

        # Área para o conteúdo comprimido do arquivo
        self.canvas = tk.Canvas(self.root, bg="grey", width=800, height=600)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Scrollbar para o conteúdo comprimido
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.config(yscrollcommand=self.scrollbar.set)

        # Botão para carregar o arquivo CSV
        self.load_button = tk.Button(self.root, text="Abrir Arquivo CSV", command=self.load_file)
        self.load_button.pack(pady=20)

        self.file_content = []
        self.compressed_height = 600
        self.font_size = 4  # Tamanho da fonte para "zoom out"
        self.line_height = 10  # Altura de cada linha no canvas comprimido

    def load_file(self):
        # Escolher o arquivo para visualizar
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        
        if file_path:
            with open(file_path, "r") as file:
                reader = csv.reader(file)
                header = next(reader)  # Pular o cabeçalho
                
                # Pegar as 44 primeiras colunas de cada linha (ignorando colunas extras)
                self.file_content = [row[:44] for row in reader]
                
                self.display_compressed_content()

    def display_compressed_content(self):
        self.canvas.delete("all")  # Limpar conteúdo anterior

        total_lines = len(self.file_content)
        visible_lines = self.compressed_height // self.line_height

        # Ajustar o número de linhas visíveis para a visualização "zoom out"
        for i in range(total_lines):
            row = self.file_content[i]
            text = ', '.join(row)
            y_position = i * self.line_height
            # Desenhando o texto no canvas de forma compacta
            self.canvas.create_text(10, y_position, anchor="nw", text=text, font=("Arial", self.font_size))

        # Atualizar a região visível do canvas
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

if __name__ == "__main__":
    root = tk.Tk()
    app = CompressedCSVView(root)
    root.mainloop()
