// file_obfuscator.js
// Automatic file obfuscation for uploads to risky domains

console.log('[EdgeDLP] File obfuscator loaded');

/**
 * Intercept file uploads and obfuscate files before upload
 */
function interceptFileUploads() {
  // Check if we're on a risky domain (may not be set yet)
  const hostname = window.location.hostname;
  const riskyDomains = [
    'chat.openai.com', 'chatgpt.com', 'claude.ai', 
    'gemini.google.com', 'copilot.microsoft.com'
  ];
  const isRisky = riskyDomains.some(domain => 
    hostname === domain || hostname.endsWith('.' + domain)
  );
  
  if (!isRisky) {
    console.log('[EdgeDLP] Not a risky domain, skipping file interception');
    return;
  }
  
  console.log('[EdgeDLP] Intercepting file uploads on risky domain:', hostname);
  
  // Find all file input elements
  const fileInputs = document.querySelectorAll('input[type="file"]');
  console.log('[EdgeDLP] Found', fileInputs.length, 'file input(s)');
  
  fileInputs.forEach(input => {
    if (input.__edgeFileIntercepted) return;
    input.__edgeFileIntercepted = true;
    
    console.log('[EdgeDLP] Intercepting file input:', input);
    
    input.addEventListener('change', async (e) => {
      // Prevent multiple processing
      if (input.__edgeProcessing || input.__edgeFilesReplaced) {
        console.log('[EdgeDLP] Already processing files or files were just replaced, skipping...');
        // Don't prevent default or stop propagation - let ChatGPT handle it
        return;
      }
      
      const files = Array.from(e.target.files);
      if (files.length === 0) return;
      
      // Check if all files are already obfuscated
      const allAlreadyObfuscated = files.every(f => 
        f.name.includes('_safe.') || f.name.includes('_safe_')
      );
      if (allAlreadyObfuscated) {
        console.log('[EdgeDLP] All files already obfuscated, skipping...');
        return; // Let the normal upload proceed
      }
      
      // CRITICAL: Prevent default AND stop propagation to prevent original file upload
      e.preventDefault();
      e.stopImmediatePropagation(); // Stop ChatGPT from processing the original file
      
      // Mark as processing
      input.__edgeProcessing = true;
      
      console.log('[EdgeDLP] File upload detected:', files.length, 'file(s)');
      console.log('[EdgeDLP] Original file upload PREVENTED - will upload obfuscated version only');
      
      // Process each file
      const obfuscatedFiles = [];
      for (const file of files) {
        console.log('[EdgeDLP] Processing file:', file.name, file.type, file.size);
        
        // Skip files that are already obfuscated (have _safe in name)
        if (file.name.includes('_safe.') || file.name.includes('_safe_')) {
          console.log('[EdgeDLP] File already obfuscated, skipping:', file.name);
          obfuscatedFiles.push(file); // Keep as-is
          continue;
        }
        
        // Check if extension context is still valid
        if (!chrome.runtime || !chrome.runtime.id) {
          console.error('[EdgeDLP] Extension context invalidated - cannot obfuscate');
          console.error('[EdgeDLP] Please refresh this page to use file obfuscation');
          obfuscatedFiles.push(file); // Keep original
          continue;
        }
        
        // Check if file type is supported
        const supportedTypes = {
          'text/x-python': 'code',
          'application/javascript': 'code',
          'text/javascript': 'code',
          'application/x-python-code': 'code',
          'application/pdf': 'pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
          'application/msword': 'docx'
        };
        
        // Also check by extension
        const ext = file.name.split('.').pop()?.toLowerCase();
        const extMap = {
          'py': 'code', 'js': 'code', 'java': 'code', 'cpp': 'code', 'c': 'code',
          'ts': 'code', 'go': 'code', 'rs': 'code',
          'pdf': 'pdf',
          'docx': 'docx', 'doc': 'docx',
          'txt': 'text', 'text': 'text', 'md': 'text', 'markdown': 'text',
          'log': 'text', 'csv': 'text'
        };
        
        const fileType = supportedTypes[file.type] || extMap[ext];
        
        if (!fileType) {
          console.log('[EdgeDLP] File type not supported for obfuscation:', file.type, ext);
          obfuscatedFiles.push(file); // Keep original
          continue;
        }
        
        try {
          // Read file content based on file type
          let fileContent;
          if (fileType === 'pdf' || fileType === 'docx') {
            // For binary files, read as ArrayBuffer and convert to base64
            console.log('[EdgeDLP] Reading binary file as ArrayBuffer...');
            const arrayBuffer = await readFileAsArrayBuffer(file);
            // Convert ArrayBuffer to base64
            const bytes = new Uint8Array(arrayBuffer);
            let binary = '';
            for (let i = 0; i < bytes.length; i++) {
              binary += String.fromCharCode(bytes[i]);
            }
            fileContent = btoa(binary); // Base64 encode
            console.log('[EdgeDLP] Binary file encoded to base64:', fileContent.length, 'chars');
          } else {
            // For text files, read as text
            fileContent = await readFileAsText(file);
            console.log('[EdgeDLP] File content read:', fileContent.length, 'chars');
          }
          
          // Send to native host for obfuscation
          console.log('[EdgeDLP] Sending to native host for obfuscation...');
          const obfuscatedContent = await obfuscateFile(fileContent, fileType, file.name, fileType === 'pdf' || fileType === 'docx');
          
          if (obfuscatedContent) {
            console.log('[EdgeDLP] Received obfuscated content:', obfuscatedContent.length, 'chars');
            
            // For binary files (PDF/DOCX), obfuscatedContent is base64
            let finalContent = obfuscatedContent;
            if (fileType === 'pdf' || fileType === 'docx') {
              // Decode base64
              try {
                const binaryString = atob(obfuscatedContent);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                  bytes[i] = binaryString.charCodeAt(i);
                }
                finalContent = bytes.buffer;
              } catch (e) {
                console.error('[EdgeDLP] Error decoding base64:', e);
                obfuscatedFiles.push(file);
                continue;
              }
            }
            
            // Create new file with obfuscated content
            const obfuscatedFile = new File(
              [finalContent],
              getObfuscatedFileName(file.name),
              { 
                type: file.type,
                lastModified: file.lastModified
              }
            );
            
            obfuscatedFiles.push(obfuscatedFile);
            console.log('[EdgeDLP] File obfuscated:', file.name, '->', obfuscatedFile.name);
            console.log('[EdgeDLP] Obfuscated file size:', obfuscatedFile.size, 'bytes');
            
            // Show notification
            showFileObfuscationNotification(file.name, obfuscatedFile.name);
          } else {
            console.error('[EdgeDLP] Obfuscation failed, keeping original');
            obfuscatedFiles.push(file);
          }
        } catch (error) {
          console.error('[EdgeDLP] Error obfuscating file:', error);
          obfuscatedFiles.push(file); // Keep original on error
        }
      }
      
      // Replace files in input
      if (obfuscatedFiles.length > 0) {
        console.log('[EdgeDLP] Replacing files in input:', obfuscatedFiles.map(f => f.name));
        
        const dataTransfer = new DataTransfer();
        obfuscatedFiles.forEach(f => {
          dataTransfer.items.add(f);
          console.log('[EdgeDLP] Added to DataTransfer:', f.name, f.size, 'bytes');
        });
        
        // Use a flag to prevent re-processing
        input.__edgeFilesReplaced = true;
        
        // Replace files - this should trigger ChatGPT's file handler
        try {
          input.files = dataTransfer.files;
          console.log('[EdgeDLP] Files replaced in input. New file count:', input.files.length);
          
          // Trigger change event so ChatGPT picks it up
          // Use a small delay to ensure files are set
          setTimeout(() => {
            // Create a new change event
            const changeEvent = new Event('change', { 
              bubbles: true, 
              cancelable: true 
            });
            
            // Dispatch it - ChatGPT should pick this up
            console.log('[EdgeDLP] Dispatching change event for ChatGPT...');
            input.dispatchEvent(changeEvent);
            
            // Also try input event
            const inputEvent = new Event('input', { 
              bubbles: true, 
              cancelable: true 
            });
            input.dispatchEvent(inputEvent);
            
            console.log('[EdgeDLP] Events dispatched. ChatGPT should process files now.');
            
            // Reset flag after events are dispatched
            setTimeout(() => {
              input.__edgeFilesReplaced = false;
            }, 2000);
          }, 200);
        } catch (error) {
          console.error('[EdgeDLP] Error replacing files:', error);
          input.__edgeFilesReplaced = false;
        }
      } else {
        console.log('[EdgeDLP] No obfuscated files to replace');
      }
      
      // Reset processing flag after a delay
      setTimeout(() => {
        input.__edgeProcessing = false;
      }, 2000); // Increased delay to prevent rapid re-processing
    }, true); // Use capture phase to intercept before other handlers
  });
}

/**
 * Read file as text
 */
function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

/**
 * Read file as ArrayBuffer (for binary files like PDF/DOCX)
 */
function readFileAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

/**
 * Obfuscate file content via native host
 */
function obfuscateFile(content, fileType, fileName, isBinary = false) {
  return new Promise((resolve) => {
    // Check if extension context is still valid
    if (!chrome.runtime || !chrome.runtime.id) {
      console.error('[EdgeDLP] Extension context invalidated - extension was reloaded');
      console.error('[EdgeDLP] Please refresh this page to use file obfuscation');
      resolve(null);
      return;
    }
    
    // Set a timeout to prevent hanging
    const timeout = setTimeout(() => {
      console.error('[EdgeDLP] File obfuscation timeout after 30 seconds');
      resolve(null);
    }, 30000);
    
    try {
      chrome.runtime.sendMessage({
        type: 'obfuscate-file',
        content: content,
        fileType: fileType,
        fileName: fileName,
        isBinary: isBinary  // Indicate if content is base64 encoded
      }, (response) => {
        clearTimeout(timeout);
        
        if (chrome.runtime.lastError) {
          const errorMsg = chrome.runtime.lastError.message;
          console.error('[EdgeDLP] Error obfuscating file:', errorMsg);
          
          // Handle extension context invalidated
          if (errorMsg.includes('Extension context invalidated') || 
              errorMsg.includes('message port closed') ||
              errorMsg.includes('Receiving end does not exist')) {
            console.warn('[EdgeDLP] Extension was reloaded. Please refresh this page.');
            // Show user-friendly message
            alert('Extension was reloaded. Please refresh this page to use file obfuscation.');
          }
          
          resolve(null);
          return;
        }
        
        if (response && response.obfuscated) {
          console.log('[EdgeDLP] File obfuscation successful:', response.obfuscated.length, 'chars');
          resolve(response.obfuscated);
        } else {
          console.error('[EdgeDLP] File obfuscation failed:', response);
          resolve(null);
        }
      });
    } catch (e) {
      clearTimeout(timeout);
      console.error('[EdgeDLP] Exception sending message:', e);
      resolve(null);
    }
  });
}

/**
 * Generate obfuscated filename
 */
function getObfuscatedFileName(originalName) {
  const ext = originalName.split('.').pop();
  const nameWithoutExt = originalName.substring(0, originalName.lastIndexOf('.'));
  return `${nameWithoutExt}_safe.${ext}`;
}

/**
 * Show notification when file is obfuscated
 */
function showFileObfuscationNotification(originalName, obfuscatedName) {
  // Create a temporary notification element
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #4CAF50;
    color: white;
    padding: 15px 20px;
    border-radius: 5px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    z-index: 10000;
    font-family: Arial, sans-serif;
    font-size: 14px;
    max-width: 300px;
  `;
  notification.innerHTML = `
    <strong>✓ File Obfuscated</strong><br>
    ${originalName} → ${obfuscatedName}
  `;
  
  document.body.appendChild(notification);
  
  // Remove after 3 seconds
  setTimeout(() => {
    notification.remove();
  }, 3000);
}

/**
 * Intercept drag and drop file uploads
 */
function interceptDragAndDrop() {
  // Check if we're on a risky domain
  const hostname = window.location.hostname;
  const riskyDomains = [
    'chat.openai.com', 'chatgpt.com', 'claude.ai', 
    'gemini.google.com', 'copilot.microsoft.com'
  ];
  const isRisky = riskyDomains.some(domain => 
    hostname === domain || hostname.endsWith('.' + domain)
  );
  
  if (!isRisky) return;
  
  // Watch for dynamically created file inputs
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1) {
          // Check if it's a file input
          if (node.tagName === 'INPUT' && node.type === 'file') {
            interceptFileInput(node);
          }
          // Check children
          if (node.querySelectorAll) {
            node.querySelectorAll('input[type="file"]').forEach((input) => {
              if (!input.__edgeFileIntercepted) {
                interceptFileInput(input);
              }
            });
          }
        }
      });
    });
  });
  
  observer.observe(document.body, { childList: true, subtree: true });
}

/**
 * Intercept a single file input (helper function)
 */
function interceptFileInput(input) {
  if (input.__edgeFileIntercepted) return;
  input.__edgeFileIntercepted = true;
  
  console.log('[EdgeDLP] Intercepting file input:', input);
  
    input.addEventListener('change', async (e) => {
      // Prevent multiple processing
      if (input.__edgeProcessing || input.__edgeFilesReplaced) {
        console.log('[EdgeDLP] Already processing files or files were just replaced, skipping...');
        return; // Let it proceed normally
      }
      
      const files = Array.from(e.target.files);
      if (files.length === 0) return;
      
      // Check if all files are already obfuscated
      const allAlreadyObfuscated = files.every(f => 
        f.name.includes('_safe.') || f.name.includes('_safe_')
      );
      if (allAlreadyObfuscated) {
        console.log('[EdgeDLP] All files already obfuscated, skipping...');
        return; // Let the normal upload proceed
      }
      
      // CRITICAL: Prevent default AND stop propagation to prevent original file upload
      e.preventDefault();
      e.stopImmediatePropagation(); // Stop ChatGPT from processing the original file
      
      // Mark as processing
      input.__edgeProcessing = true;
      
      console.log('[EdgeDLP] Original file upload PREVENTED - will upload obfuscated version only');
    
    console.log('[EdgeDLP] File upload detected:', files.length, 'file(s)');
    
    // Process each file (same logic as interceptFileUploads)
    const obfuscatedFiles = [];
    for (const file of files) {
      console.log('[EdgeDLP] Processing file:', file.name, file.type, file.size);
      
      // Skip files that are already obfuscated (have _safe in name)
      if (file.name.includes('_safe.') || file.name.includes('_safe_')) {
        console.log('[EdgeDLP] File already obfuscated, skipping:', file.name);
        obfuscatedFiles.push(file); // Keep as-is
        continue;
      }
      
      // Check if extension context is still valid
      if (!chrome.runtime || !chrome.runtime.id) {
        console.error('[EdgeDLP] Extension context invalidated - cannot obfuscate');
        console.error('[EdgeDLP] Please refresh this page to use file obfuscation');
        obfuscatedFiles.push(file); // Keep original
        continue;
      }
      
      // Check if file type is supported
      const ext = file.name.split('.').pop()?.toLowerCase();
      const extMap = {
        'py': 'code', 'js': 'code', 'java': 'code', 'cpp': 'code', 'c': 'code',
        'ts': 'code', 'go': 'code', 'rs': 'code',
        'pdf': 'pdf',
        'docx': 'docx', 'doc': 'docx',
        'txt': 'text', 'text': 'text', 'md': 'text', 'markdown': 'text',
        'log': 'text', 'csv': 'text'
      };
      
      const fileType = extMap[ext];
      
      if (!fileType) {
        console.log('[EdgeDLP] File type not supported:', ext);
        obfuscatedFiles.push(file);
        continue;
      }
      
      try {
        // Read file content based on file type
        let fileContent;
        if (fileType === 'pdf' || fileType === 'docx') {
          // For binary files, read as ArrayBuffer and convert to base64
          console.log('[EdgeDLP] Reading binary file as ArrayBuffer...');
          const arrayBuffer = await readFileAsArrayBuffer(file);
          // Convert ArrayBuffer to base64
          const bytes = new Uint8Array(arrayBuffer);
          let binary = '';
          for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          fileContent = btoa(binary); // Base64 encode
          console.log('[EdgeDLP] Binary file encoded to base64:', fileContent.length, 'chars');
        } else {
          // For text files, read as text
          fileContent = await readFileAsText(file);
          console.log('[EdgeDLP] File content read:', fileContent.length, 'chars');
        }
        
        const obfuscatedContent = await obfuscateFile(fileContent, fileType, file.name, fileType === 'pdf' || fileType === 'docx');
        
        if (obfuscatedContent) {
          const obfuscatedFile = new File(
            [obfuscatedContent],
            getObfuscatedFileName(file.name),
            { type: file.type }
          );
          obfuscatedFiles.push(obfuscatedFile);
          showFileObfuscationNotification(file.name, obfuscatedFile.name);
        } else {
          obfuscatedFiles.push(file);
        }
      } catch (error) {
        console.error('[EdgeDLP] Error obfuscating file:', error);
        obfuscatedFiles.push(file);
      }
    }
    
    // Replace files in input
    if (obfuscatedFiles.length > 0) {
      console.log('[EdgeDLP] Replacing files in input:', obfuscatedFiles.map(f => f.name));
      
      const dataTransfer = new DataTransfer();
      obfuscatedFiles.forEach(f => {
        dataTransfer.items.add(f);
        console.log('[EdgeDLP] Added to DataTransfer:', f.name, f.size, 'bytes');
      });
      
      // Use a flag to prevent re-processing
      input.__edgeFilesReplaced = true;
      
      // Replace files - this should trigger ChatGPT's file handler
      try {
        input.files = dataTransfer.files;
        console.log('[EdgeDLP] Files replaced in input. New file count:', input.files.length);
        
        // ChatGPT needs to see the change event to process the OBFUSCATED files
        // Use a small delay to ensure files are set
        setTimeout(() => {
          console.log('[EdgeDLP] Obfuscated files are set, triggering ChatGPT upload...');
          console.log('[EdgeDLP] Input files before dispatch:', input.files.length, 'file(s)');
          console.log('[EdgeDLP] File names:', Array.from(input.files).map(f => f.name));
          
          // Verify we have obfuscated files (should have _safe in name)
          const fileNames = Array.from(input.files).map(f => f.name);
          const allObfuscated = fileNames.every(name => name.includes('_safe.') || name.includes('_safe_'));
          if (!allObfuscated) {
            console.warn('[EdgeDLP] WARNING: Some files are not obfuscated!', fileNames);
          }
          
          // Create a synthetic change event that ChatGPT will recognize
          // This will trigger ChatGPT's file upload handler with the OBFUSCATED file
          const changeEvent = new Event('change', { 
            bubbles: true, 
            cancelable: false  // Don't allow cancellation - we want ChatGPT to process it
          });
          
          // Also create an InputEvent which some frameworks prefer
          const inputEvent = new InputEvent('input', {
            bubbles: true,
            cancelable: false,
            inputType: 'insertText',
            data: null
          });
          
          // Dispatch input event first (some frameworks listen to this)
          console.log('[EdgeDLP] Dispatching input event for ChatGPT (obfuscated file)...');
          input.dispatchEvent(inputEvent);
          
          // Then dispatch change event (standard file input event)
          // This will trigger ChatGPT to upload the OBFUSCATED file
          console.log('[EdgeDLP] Dispatching change event for ChatGPT (obfuscated file)...');
          input.dispatchEvent(changeEvent);
          
          // Also try a custom event that might trigger ChatGPT's handler
          const customEvent = new CustomEvent('files-changed', {
            bubbles: true,
            cancelable: false,
            detail: { files: obfuscatedFiles }
          });
          input.dispatchEvent(customEvent);
          
          console.log('[EdgeDLP] Events dispatched. ChatGPT should process OBFUSCATED file now.');
          console.log('[EdgeDLP] Input files after dispatch:', input.files.length, 'file(s)');
          console.log('[EdgeDLP] Final file names:', Array.from(input.files).map(f => f.name));
          
          // Reset flag after events are dispatched
          setTimeout(() => {
            input.__edgeFilesReplaced = false;
          }, 2000);
        }, 200); // Slightly longer delay to ensure files are fully set
      } catch (error) {
        console.error('[EdgeDLP] Error replacing files:', error);
        input.__edgeFilesReplaced = false;
      }
    } else {
      console.log('[EdgeDLP] No obfuscated files to replace');
    }
    
    // Reset processing flag after a delay
    setTimeout(() => {
      input.__edgeProcessing = false;
    }, 2000); // Increased delay to prevent rapid re-processing
  }, true); // Use capture phase
}

// Auto-start on risky domains
(function() {
  const hostname = window.location.hostname;
  const riskyDomains = [
    'chat.openai.com', 'chatgpt.com', 'claude.ai', 
    'gemini.google.com', 'copilot.microsoft.com'
  ];
  const isRisky = riskyDomains.some(domain => 
    hostname === domain || hostname.endsWith('.' + domain)
  );
  
  if (isRisky) {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
          interceptFileUploads();
          interceptDragAndDrop();
        }, 1000);
      });
    } else {
      setTimeout(() => {
        interceptFileUploads();
        interceptDragAndDrop();
      }, 1000);
    }
  }
})();

// Export functions
if (typeof window !== 'undefined') {
  window.edgeFileObfuscator = {
    interceptFileUploads,
    interceptDragAndDrop
  };
}

