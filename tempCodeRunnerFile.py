
@app.route('/admin/admin_dashboard/<int:user_id>', methods=['POST','GET'])
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
        flash('You must be an admin to reject users.', 'error')
        return redirect(url_for('home'))

    user_to_reject = db_session.query(User).filter_by(id=user_id).one_or_none()
    if user_to_reject:
        db_session.delete(user_to_reject)
        db_session.commit()
        flash(f'User {user_to_reject.username} has been rejected and deleted!', 'info')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('admin_dashboard'))