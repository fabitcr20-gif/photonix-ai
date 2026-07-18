/**
 * Componente de carga: soporta carga individual (un archivo) y carga masiva
 * por carpeta completa (webkitdirectory), cumpliendo el requerimiento del
 * Módulo de Carga de Archivos.
 */
"use client";

import { useCallback, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FolderUp } from "lucide-react";

interface DropzoneProps {
  mode: "single" | "folder";
  onFilesSelected: (files: File[]) => void;
}

export default function Dropzone({ mode, onFilesSelected }: DropzoneProps) {
  const [fileCount, setFileCount] = useState(0);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback(
    (accepted: File[]) => {
      setFileCount(accepted.length);
      onFilesSelected(accepted);
    },
    [onFilesSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: mode === "folder",
    accept: {
      "image/*": [".jpg", ".jpeg", ".png", ".tiff", ".heic"],
      "application/octet-stream": [".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"],
    },
  });

  function handleFolderInput(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    setFileCount(files.length);
    onFilesSelected(files);
  }

  if (mode === "folder") {
    return (
      <div
        onClick={() => folderInputRef.current?.click()}
        className="border-2 border-dashed border-photonix-border rounded-xl2 p-10 text-center cursor-pointer hover:border-photonix-accent transition-colors"
      >
        <FolderUp className="mx-auto mb-3 text-photonix-steel" size={36} />
        <p className="font-medium">Selecciona una carpeta completa</p>
        <p className="text-sm text-photonix-textMuted mt-1">
          Se cargarán todas las fotos compatibles (RAW, JPEG, PNG, TIFF, HEIC, DNG y más).
        </p>
        {fileCount > 0 && (
          <p className="text-sm text-photonix-accent mt-3">{fileCount} archivos seleccionados</p>
        )}
        <input
          ref={folderInputRef}
          type="file"
          // @ts-expect-error: atributo no estándar pero soportado por navegadores modernos
          webkitdirectory=""
          directory=""
          multiple
          className="hidden"
          onChange={handleFolderInput}
        />
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl2 p-10 text-center cursor-pointer transition-colors ${
        isDragActive ? "border-photonix-accent" : "border-photonix-border hover:border-photonix-accent"
      }`}
    >
      <input {...getInputProps()} />
      <UploadCloud className="mx-auto mb-3 text-photonix-steel" size={36} />
      <p className="font-medium">Arrastra una foto aquí o haz clic para elegir</p>
      <p className="text-sm text-photonix-textMuted mt-1">JPG, PNG, TIFF, HEIC o RAW</p>
      {fileCount > 0 && (
        <p className="text-sm text-photonix-accent mt-3">{fileCount} archivo seleccionado</p>
      )}
    </div>
  );
}
