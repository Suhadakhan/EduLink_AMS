function uni_modal(title, url, size) {
    $.ajax({
        url: url,
        error: err => {
            console.log(err);
            Swal.fire('Error', 'An error occurred', 'error');
        },
        success: function(resp) {
            if (resp) {
                $('#uni_modal .modal-title').html(title);
                $('#uni_modal .modal-body').html(resp);
                $('#uni_modal').modal('show');
                
                // Handle form submission
                $('#uni_modal form').submit(function(e) {
                    e.preventDefault();
                    $.ajax({
                        url: $(this).attr('action'),
                        data: new FormData($(this)[0]),
                        cache: false,
                        contentType: false,
                        processData: false,
                        method: 'POST',
                        type: 'POST',
                        success: function(resp) {
                            if (resp.status === 'success') {
                                $('#uni_modal').modal('hide');
                                Swal.fire({
                                    title: 'Success!',
                                    text: resp.message || 'Operation completed successfully',
                                    icon: 'success',
                                    timer: 1500,
                                    showConfirmButton: false
                                }).then(() => {
                                    location.reload();
                                });
                            } else {
                                Swal.fire('Error', resp.message || 'An error occurred', 'error');
                            }
                        }
                    });
                });
            }
        }
    });
} 